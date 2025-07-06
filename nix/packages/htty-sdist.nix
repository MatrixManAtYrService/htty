# Pure Python source distribution for htty wrapper
{ pkgs, ... }:

let
  # Get project metadata from htty pyproject.toml
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../htty/pyproject.toml);
  inherit (pyprojectToml.project) version;

in
# Build the htty package as a source distribution (.tar.gz)
pkgs.stdenv.mkDerivation {
  pname = "htty-sdist";
  inherit version;
  src = ../../htty;

  nativeBuildInputs = with pkgs; [
    python3
    python3.pkgs.hatchling
    python3.pkgs.build
  ];

  buildPhase = ''
    runHook preBuild

    # Build source distribution only (no wheel)
    python -m build --sdist --outdir dist/

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out
    cp dist/*.tar.gz $out/

    # Store sdist metadata for consumers
    SDIST_FILE=$(ls $out/*.tar.gz | head -1)
    SDIST_NAME=$(basename "$SDIST_FILE")

    echo "$SDIST_NAME" > "$out/sdist-filename.txt"
    echo "$SDIST_FILE" > "$out/sdist-path.txt"

    echo "Built htty source distribution: $SDIST_NAME"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - Python wrapper source distribution";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
