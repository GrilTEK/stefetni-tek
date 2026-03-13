#!/usr/bin/env node
// Creates mobile/www -> ../frontend symlink if absent
const fs = require("fs");
const path = require("path");

const mobileDir = path.resolve(__dirname, "..");
const wwwPath = path.join(mobileDir, "www");
const target = "../frontend";

if (fs.existsSync(wwwPath)) {
  const stat = fs.lstatSync(wwwPath);
  if (stat.isSymbolicLink()) {
    const existing = fs.readlinkSync(wwwPath);
    if (existing === target) {
      console.log("www symlink already exists and is correct.");
      process.exit(0);
    }
    console.log(`Removing stale symlink: www -> ${existing}`);
    fs.unlinkSync(wwwPath);
  } else {
    console.error("ERROR: mobile/www exists but is not a symlink. Remove it manually.");
    process.exit(1);
  }
}

fs.symlinkSync(target, wwwPath);
console.log(`Created symlink: mobile/www -> ${target}`);
