{
  description = "htty - Headless Terminal with Python bindings";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    rust-overlay.url = "github:oxalica/rust-overlay";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, rust-overlay, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        overlays = [ rust-overlay.overlays.default ];
        pkgs = import nixpkgs { inherit system overlays; };

        rustToolchain = pkgs.rust-bin.stable.latest.default.override {
          extensions = [ "rust-src" "clippy" "rustfmt" ];
        };

        # Get project metadata
        cargoToml = builtins.fromTOML (builtins.readFile ./Cargo.toml);
        inherit (cargoToml.package) version;

        # Main Rust package (just the ht binary)
        htty-rust = pkgs.rustPlatform.buildRustPackage {
          pname = "htty";
          inherit version;
          src = ./.;

          cargoLock = {
            lockFile = ./Cargo.lock;
          };

          nativeBuildInputs = with pkgs; [
            pkg-config
            rustToolchain
          ];

          buildInputs = with pkgs; [
            # Add any required libraries here
          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            libiconv
            darwin.apple_sdk.frameworks.Foundation
          ];

          # Build just the binary, not the library
          cargoBuildFlags = [ "--bin" "ht" ];
          cargoTestFlags = [ "--bin" "ht" ];

          meta = with pkgs.lib; {
            description = "Headless Terminal - Rust binary for terminal automation";
            homepage = "https://github.com/MatrixManAtYrService/ht";
            license = licenses.mit;
            mainProgram = "ht";
            platforms = platforms.unix;
          };
        };

        # Python wheel with Rust bindings using rustPlatform.buildRustPackage approach
        htty-wheel = pkgs.python312.pkgs.buildPythonPackage {
          pname = "htty-wheel";
          inherit version;
          src = ./.;
          format = "pyproject";

          cargoDeps = pkgs.rustPlatform.importCargoLock {
            lockFile = ./Cargo.lock;
          };

          nativeBuildInputs = with pkgs; [
            rustToolchain
            pkg-config
            maturin
            rustPlatform.cargoSetupHook
            rustPlatform.maturinBuildHook
          ];

          buildInputs = with pkgs; [
            # Add any required libraries here
          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            libiconv
            darwin.apple_sdk.frameworks.Foundation
          ];

          # Configure maturin to use python features
          maturinBuildFlags = [ "--features" "python" ];

          meta = with pkgs.lib; {
            description = "Headless Terminal - Python wheel with Rust bindings";
            homepage = "https://github.com/MatrixManAtYrService/ht";
            license = licenses.mit;
            platforms = platforms.unix;
          };
        };

      in
      {
        packages = {
          default = htty-rust;
          htty = htty-rust;
          htty-wheel = htty-wheel;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Rust development
            rustToolchain
            pkg-config
            maturin
            
            # Python development  
            python3
            python3.pkgs.pip
            python3.pkgs.pytest
            
            # Additional tools
            ruff
          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            libiconv
            darwin.apple_sdk.frameworks.Foundation
          ];

          shellHook = ''
            echo "🚀 htty development environment ready!"
            echo "📦 To build Python package: maturin develop --features python"
            echo "🧪 To run tests: python -m pytest"
            echo "🔧 Rust binary: cargo build --release"
            echo "🎯 To build wheel: nix build .#htty-wheel"
            
            # Set up environment for maturin
            export PYO3_NO_RECOMPILE=1
            export CARGO_TARGET_DIR="./target"
          '';
        };
      }
    );
}
