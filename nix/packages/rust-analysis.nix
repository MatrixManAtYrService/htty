# Rust code analysis tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage rustClippyCheck;
in
createAnalysisPackage {
  name = "rust-analysis";
  description = "Rust code analysis";
  checks = {
    clippy = rustClippyCheck;
  };
}
