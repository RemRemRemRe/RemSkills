#!/usr/bin/env node
// Cross-session coordination for one project directory: path claims and resource leases.
// Zero dependencies, works on POSIX and Windows.
//
//   node lease.mjs [--dir <lock-dir>] [--session <id>] claim <path>...
//   node lease.mjs [--dir ...] unclaim <path>...
//   node lease.mjs [--dir ...] status
//   node lease.mjs [--dir ...] acquire <resource> [--ttl 600] [--wait 120] [--intent <text>] [--force]
//   node lease.mjs [--dir ...] release <resource> [--force]
//   node lease.mjs [--dir ...] run <resource> [--ttl 600] [--wait 120] [--intent <text>] -- <command...>
//
// The lock directory defaults to `<cwd>/.agents/locks`; LEASE_DIR overrides it, and every session of
// the project must point at the same directory. The session id comes from --session, PI_SESSION_ID,
// LEASE_SESSION, or host-pid.
//
// Leases are exclusive per resource key. `run` holds the lease for the command's lifetime, carries its
// pid and renews the TTL; `acquire` is TTL-only (release it when done). A lease is taken over when its
// holder is dead, or when a manual lease's TTL expired; a live holder is never stolen without --force.
// Exit codes: 0 success, 1 refused or invalid usage, the child's code for `run`.

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const args = process.argv.slice(2);
const sep = args.indexOf('--');
const head = sep >= 0 ? args.slice(0, sep) : args;
const tail = sep >= 0 ? args.slice(sep + 1) : [];

const BOOLEAN_FLAGS = new Set(['force', 'json']);
const flags = {};
const positional = [];
for (let i = 0; i < head.length; i++) {
  const a = head[i];
  if (!a.startsWith('--')) { positional.push(a); continue; }
  const key = a.slice(2);
  const next = head[i + 1];
  if (!BOOLEAN_FLAGS.has(key) && next !== undefined && !next.startsWith('--')) { flags[key] = next; i++; }
  else flags[key] = true;
}
const cmd = positional.shift();

const dir = path.resolve(flags.dir || process.env.LEASE_DIR || path.join(process.cwd(), '.agents', 'locks'));
const session = String(flags.session || process.env.PI_SESSION_ID || process.env.LEASE_SESSION || `${os.hostname()}-${process.pid}`);
const leaseDir = path.join(dir, 'leases');
const claimDir = path.join(dir, 'claims');
fs.mkdirSync(leaseDir, { recursive: true });
fs.mkdirSync(claimDir, { recursive: true });

const keyOf = (resource) => String(resource || '').replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
const leasePath = (resource) => path.join(leaseDir, keyOf(resource) + '.json');
const claimPath = (id = session) => path.join(claimDir, String(id).replace(/[^A-Za-z0-9._-]+/g, '-') + '.json');
const readJson = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; } };
const alive = (pid) => { if (!Number.isInteger(pid) || pid <= 0) return false; try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };
const seconds = (ms) => Math.max(0, Math.round(ms / 1000));
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
const fail = (msg) => { console.error('lease: ' + msg); process.exit(1); };

const readLease = (resource) => { const p = leasePath(resource); const info = readJson(p); return info ? { ...info, path: p } : null; };

function takeOver(info, why) {
  // Remove only the entry we read: a concurrent takeover must not delete a fresh lease.
  const current = readJson(info.path);
  if (!current || current.started !== info.started) return false;
  fs.rmSync(info.path, { force: true });
  console.error(`lease: took over ${path.basename(info.path, '.json')} from ${info.session} (${why})`);
  return true;
}

function acquire(resource, { ttl, wait, intent, force, manual }) {
  const key = keyOf(resource);
  if (!key) fail('empty resource name');
  const p = leasePath(key);
  const deadline = Date.now() + wait * 1000;
  for (;;) {
    try {
      const fd = fs.openSync(p, 'wx');
      const info = { resource: key, session, pid: manual ? 0 : process.pid, intent: String(intent || ''), started: Date.now(), expires: Date.now() + ttl * 1000 };
      fs.writeSync(fd, JSON.stringify(info, null, 2));
      fs.closeSync(fd);
      return info;
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
    }
    const info = readLease(key);
    if (info) {
      const holderDead = !!info.pid && !alive(info.pid);
      const expired = Number(info.expires) < Date.now();
      const why = holderDead ? 'holder is dead' : expired ? `expired ${seconds(Date.now() - info.expires)}s ago` : 'released';
      if (holderDead || (expired && (force || !info.pid))) { if (takeOver(info, why)) continue; }
      if (Date.now() >= deadline) return { held: info };
      sleep(Math.min(500, Math.max(50, deadline - Date.now())));
      continue;
    }
    sleep(200);
  }
}

function release(resource, force) {
  const info = readLease(resource);
  if (!info) return void console.error('lease: not held: ' + keyOf(resource));
  if (info.session !== session && !force) fail(`held by ${info.session}; use --force only with agreement`);
  fs.rmSync(info.path, { force: true });
}

function printLease(info) {
  const holder = info.pid ? (alive(info.pid) ? 'alive' : 'DEAD') : 'manual';
  const left = Math.round((info.expires - Date.now()) / 1000);
  console.log(`${keyOf(info.resource).padEnd(42)} ${String(info.session).padEnd(30)} ${holder.padEnd(6)} age ${String(seconds(Date.now() - info.started)).padEnd(5)} TTL ${left > 0 ? 'in ' + left + 's' : 'AGO ' + Math.abs(left) + 's'}${info.intent ? '  | ' + info.intent : ''}`);
}

function overlaps(a, b) {
  if (a === b) return true;
  const inside = (x, y) => { const rel = path.relative(x, y); return !!rel && !rel.startsWith('..') && !path.isAbsolute(rel); };
  return inside(a, b) || inside(b, a);
}

function claim(paths) {
  const own = readJson(claimPath()) || { session, paths: [] };
  const next = [...new Set([...(own.paths || []), ...paths.map((p) => path.resolve(process.cwd(), p))])];
  const conflicts = [];
  for (const f of fs.readdirSync(claimDir)) {
    if (f === path.basename(claimPath())) continue;
    const other = readJson(path.join(claimDir, f));
    if (!other || !Array.isArray(other.paths)) continue;
    for (const a of next) for (const b of other.paths) if (overlaps(a, b)) conflicts.push(`${other.session}: ${b}  (your ${a})`);
  }
  if (conflicts.length && !flags.force) {
    console.error('lease: claim conflicts with another session:');
    for (const c of conflicts) console.error('  ' + c);
    console.error('lease: split the unit, wait, or repeat with --force to record the accepted overlap');
    process.exit(1);
  }
  fs.writeFileSync(claimPath(), JSON.stringify({ session, pid: process.pid, updated: Date.now(), paths: next, overlapAccepted: conflicts.length > 0 }, null, 2));
  if (conflicts.length) console.error(`lease: accepted ${conflicts.length} overlap(s) with --force`);
  console.log(`claimed ${next.length} path(s) for ${session}`);
}

function unclaim(paths) {
  const file = claimPath();
  const own = readJson(file);
  if (!own) return void console.log('no claims for ' + session);
  const drop = new Set(paths.map((p) => path.resolve(process.cwd(), p)));
  own.paths = (own.paths || []).filter((p) => !drop.has(p));
  own.updated = Date.now();
  if (!own.paths.length) fs.rmSync(file, { force: true });
  else fs.writeFileSync(file, JSON.stringify(own, null, 2));
  console.log(`dropped ${drop.size} path(s) for ${session}`);
}

function status() {
  const leases = fs.readdirSync(leaseDir).filter((f) => f.endsWith('.json'));
  console.log(`== leases (${dir}) ==`);
  if (!leases.length) console.log('  (none)');
  for (const f of leases) { const info = readJson(path.join(leaseDir, f)); if (info) printLease(info); }
  console.log('== claims ==');
  const claims = fs.readdirSync(claimDir).filter((f) => f.endsWith('.json'));
  if (!claims.length) console.log('  (none)');
  for (const f of claims) {
    const c = readJson(path.join(claimDir, f));
    if (!c) continue;
    console.log(`  ${String(c.session).padEnd(30)} ${(c.paths || []).length} path(s) age ${seconds(Date.now() - c.updated)}s${c.overlapAccepted ? ' (overlap accepted)' : ''}`);
    for (const p of c.paths || []) console.log('    ' + p);
  }
}

const ttl = Number(flags.ttl || 600);
const wait = Number(flags.wait || 120);

switch (cmd) {
  case 'claim':
    if (!positional.length) fail('claim needs at least one path');
    claim(positional);
    break;
  case 'unclaim':
    if (!positional.length) fail('unclaim needs at least one path');
    unclaim(positional);
    break;
  case 'status':
    status();
    break;
  case 'acquire': {
    const resource = positional[0] || fail('acquire needs a resource');
    const r = acquire(resource, { ttl, wait, intent: flags.intent, force: !!flags.force, manual: true });
    if (r.held) { console.error(`lease: ${keyOf(resource)} is held by ${r.held.session} until ${new Date(r.held.expires).toISOString()}; waited ${wait}s`); process.exit(1); }
    console.log(`acquired ${keyOf(resource)} for ${session} (ttl ${ttl}s, manual: release it when done)`);
    break;
  }
  case 'release': {
    const resource = positional[0] || fail('release needs a resource');
    release(resource, !!flags.force);
    break;
  }
  case 'run': {
    const resource = positional[0] || fail('run needs a resource and `-- <command>`');
    if (!tail.length) fail('run needs `-- <command>`');
    const r = acquire(resource, { ttl, wait, intent: flags.intent, force: !!flags.force, manual: false });
    if (r.held) { console.error(`lease: ${keyOf(resource)} is held by ${r.held.session} until ${new Date(r.held.expires).toISOString()}; waited ${wait}s`); process.exit(1); }
    const timer = setInterval(() => {
      const info = readLease(resource);
      if (info && info.session === session) { info.expires = Date.now() + ttl * 1000; try { fs.writeFileSync(info.path, JSON.stringify(info, null, 2)); } catch { /* best effort */ } }
    }, Math.max(1000, Math.floor((ttl * 1000) / 3)));
    timer.unref();
    const done = () => { try { release(resource, false); } catch { /* ignore */ } };
    process.on('SIGINT', () => { done(); process.exit(130); });
    process.on('SIGTERM', () => { done(); process.exit(143); });
    const res = spawnSync(tail[0], tail.slice(1), { stdio: 'inherit' });
    done();
    process.exit(res.status === null ? 1 : res.status);
  }
  default:
    fail('usage: claim | unclaim | status | acquire | release | run  (see the skill for details)');
}
