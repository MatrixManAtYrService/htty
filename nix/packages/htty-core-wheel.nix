# Build htty-core Python wheel (maturin-built with Rust binary)
{ inputs, pkgs, targetSystem ? null, lib ? pkgs.lib, ... }:

let
  # Determine if we're cross-compiling (check both manual targetSystem and pkgsCross)
  isCrossCompiling = (targetSystem != null && targetSystem != pkgs.stdenv.hostPlatform.system)
                     || (pkgs.stdenv.hostPlatform != pkgs.stdenv.targetPlatform);

  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs {
    inherit (pkgs.stdenv.hostPlatform) system;
    inherit overlays;
  };

  # Cross-compilation target mappings
  rustTargetMap = {
    "aarch64-linux" = "aarch64-unknown-linux-gnu";
    "x86_64-linux" = "x86_64-unknown-linux-gnu";
    "aarch64-darwin" = "aarch64-apple-darwin";
    "x86_64-darwin" = "x86_64-apple-darwin";
  };

  rustTarget = if targetSystem != null then rustTargetMap.${targetSystem} else null;

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
    targets = if rustTarget != null then [ rustTarget ] else [ ];
  };

  # Get project metadata
  cargoToml = builtins.fromTOML (builtins.readFile ../../htty-core/Cargo.toml);
  inherit (cargoToml.package) version;

  # Include only files needed for htty-core wheel building
  wheelSource = inputs.nix-filter.lib {
    root = ../../htty-core;
    include = [
      "src/rust"
      "src/python"
      "assets"
      "Cargo.toml"
      "Cargo.lock"
      "pyproject.toml"
      "README.md"
    ];
  };

in
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-core-wheel";
  inherit version;
  src = wheelSource;

  cargoDeps = pkgsWithRust.rustPlatform.importCargoLock {
    lockFile = ../../htty-core/Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    rustToolchain
    pkg-config
    python3
    python3.pkgs.cffi
    maturin
    rustPlatform.cargoSetupHook
  ] ++ pkgsWithRust.lib.optionals isCrossCompiling [
    # Add zig for cross-compilation (maturin --zig approach)
    zig
  ];

  buildInputs = pkgs.lib.optionals pkgs.stdenv.isDarwin [
    pkgs.libiconv
  ];

  buildPhase = ''
    runHook preBuild

    # Set up environment for cargo and maturin
    export CARGO_TARGET_DIR="./target"

    ${if isCrossCompiling then ''
      # Cross-compilation environment for ${targetSystem}
      echo "Cross-compiling for target: ${targetSystem}"
      echo "Rust target: ${rustTarget}"

      # Following maturin cross-compilation best practices:
      # https://www.maturin.rs/distribution.html#cross-compiling
      ${if targetSystem == "aarch64-linux" && pkgs.stdenv.isDarwin then ''
        # Cross-compilation from macOS to Linux ARM64
        # This requires either:
        # 1. Docker with manylinux images (recommended for CI)
        # 2. Zig cross-compilation (--zig flag)
        # 3. Proper cross-compilation toolchain
        echo "Warning: Cross-compilation from macOS to Linux requires proper toolchain setup"
        echo "Consider using maturin with --zig flag or Docker-based CI approach"
      '' else ""}
    '' else ""}

    # Build arguments based on target
    ${if rustTarget != null then ''
      CARGO_BUILD_ARGS="--release --bin ht --target ${rustTarget}"
      # Use zig for cross-compilation (maturin best practice)
      MATURIN_BUILD_ARGS="--release --out dist/ --target ${rustTarget} --zig --compatibility manylinux_2_28"
    '' else ''
      CARGO_BUILD_ARGS="--release --bin ht"
      MATURIN_BUILD_ARGS="--release --out dist/ --compatibility manylinux_2_28"
    ''}

    # First build the Rust binary with cargo
    cargo build $CARGO_BUILD_ARGS

    # Then use maturin to package the Python module + binary
    # Note: maturin with --zig handles cross-compilation toolchain automatically
    maturin build $MATURIN_BUILD_ARGS

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    # Create output directory
    mkdir -p $out

    # Copy the built wheel
    cp dist/*.whl $out/

    # Store wheel metadata for consumers
    WHEEL_FILE=$(ls $out/*.whl | head -1)
    WHEEL_NAME=$(basename "$WHEEL_FILE")

    # Store metadata
    echo "$WHEEL_NAME" > "$out/wheel-filename.txt"
    echo "$WHEEL_FILE" > "$out/wheel-path.txt"

    echo "Built htty-core wheel package: $WHEEL_NAME"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - Rust binary with Python bindings wheel";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
