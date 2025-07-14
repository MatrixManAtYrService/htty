{ pkgs, perSystem, ... }:

let
  # Get the htty-core wheel directory from our packages
  httyCoreWheel = perSystem.self.htty-core-wheel;

  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../htty-core/pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Remove any trailing newline or whitespace
  wheelFilenameRaw = builtins.readFile "${httyCoreWheel}/wheel-filename.txt";
  wheelFilenameClean = builtins.match "[ \t\r\n]*([^\n\r \t]+)[ \t\r\n]*" wheelFilenameRaw;
  actualWheelFilename = if wheelFilenameClean != null then builtins.elemAt wheelFilenameClean 0 else throw "Could not parse wheel-filename.txt (got: '${wheelFilenameRaw}')";

  # Create the Python package by properly installing the wheel
  httyCorePkg = pkgs.python3.pkgs.buildPythonPackage {
    pname = "htty-core";
    inherit version;
    format = "wheel";

    # Use the wheel as source, dynamically determined
    src = "${httyCoreWheel}/${actualWheelFilename}";

    dontBuild = true;

    postInstall = ''
      if [ -f "$out/bin/ht" ]; then
        chmod +x "$out/bin/ht"
        echo "Found and made executable: $out/bin/ht"
      else
        echo "Looking for ht binary in wheel structure..."
        find $out -name "ht" -type f || echo "No ht binary found"
      fi
    '';

    meta = with pkgs.lib; {
      description = "Headless Terminal - Rust binary with Python bindings";
      homepage = "https://github.com/MatrixManAtYrService/ht";
      license = licenses.mit;
      platforms = platforms.unix;
    };
  };
in
(pkgs.python3.withPackages (ps: [ httyCorePkg ])).overrideAttrs (old: {
  passthru = (old.passthru or { }) // {
    tests = { };
  };
})
