# Main ht Rust binary package
{ inputs, pkgs, ... }:

let
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit (pkgs.stdenv.hostPlatform) system; 
    inherit overlays; 
  };

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
  };

  cargoToml = builtins.fromTOML (builtins.readFile ../../Cargo.toml);
  inherit (cargoToml.package) version;

  # Only include Rust-related files to avoid rebuilds on Python changes
  rustOnlySource = pkgs.lib.cleanSourceWith {
    src = ../..;
    filter = path: type:
      let
        baseName = baseNameOf path;
        # Get relative path from project root
        projectRoot = toString ../..;
        relPath = pkgs.lib.removePrefix projectRoot (toString path);
      in
        # Include Rust source files
        (pkgs.lib.hasPrefix "/src/rust" relPath) ||
        # Include assets directory (needed by rust-embed)
        (pkgs.lib.hasPrefix "/assets" relPath) ||
        # Include directory structure
        (relPath == "/src/rust" && type == "directory") ||
        (relPath == "/src" && type == "directory") ||
        (relPath == "/assets" && type == "directory") ||
        # Include Cargo files  
        (baseName == "Cargo.toml") ||
        (baseName == "Cargo.lock") ||
        # Include license and readme
        (baseName == "LICENSE") ||
        (baseName == "README.md");
  };

in
pkgsWithRust.rustPlatform.buildRustPackage {
  pname = "ht";
  inherit version;
  src = rustOnlySource;

  cargoLock = {
    lockFile = ../../Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    pkg-config
    rustToolchain
  ];

  buildInputs = [
  ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
    pkgs.libiconv
    pkgs.darwin.apple_sdk.frameworks.Foundation
  ];

  # just the binary, don't build Python bindings
  buildFeatures = [ ];

  meta = with pkgs.lib; {
    description = "Headless Terminal - Rust binary for terminal automation";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    mainProgram = "ht";
    platforms = platforms.unix;
  };
}
