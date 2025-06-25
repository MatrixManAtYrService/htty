# Main htty Rust binary package
{ inputs, pkgs, ... }:

let
  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit (pkgs.stdenv.hostPlatform) system; 
    inherit overlays; 
  };

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
  };

  # Get project metadata
  cargoToml = builtins.fromTOML (builtins.readFile ../../Cargo.toml);
  inherit (cargoToml.package) version;

in
pkgsWithRust.rustPlatform.buildRustPackage {
  pname = "htty";
  inherit version;
  src = ../..;

  cargoLock = {
    lockFile = ../../Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    pkg-config
    rustToolchain
  ];

  buildInputs = with pkgsWithRust; [
    # Add any required libraries here
  ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
    pkgs.libiconv
    pkgs.darwin.apple_sdk.frameworks.Foundation
  ];

  # Build features - by default just the binary, not Python bindings
  buildFeatures = [ ];

  meta = with pkgs.lib; {
    description = "Headless Terminal - Rust binary for terminal automation";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    mainProgram = "ht";
    platforms = platforms.unix;
  };
}
