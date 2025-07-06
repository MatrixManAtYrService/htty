# Create Python environment with htty-core installed
{ pkgs, perSystem, ... }:

let
  # Get the htty-core wheel from our packages
  httyCoreWheel = perSystem.self.htty-core-wheel;

  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../htty-core/pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Create the Python package by properly installing the wheel
  httyCorePkg = pkgs.python3.pkgs.buildPythonPackage {
    pname = "htty-core";
    inherit version;
    format = "wheel";

    # Use the wheel as source
    src = "${httyCoreWheel}/htty_core-${version}-py3-none-macosx_11_0_arm64.whl";

    # Don't try to build - it's already built
    dontBuild = true;

    # Extract and install scripts properly
    postInstall = ''
      # The wheel should have installed scripts to $out/bin already
      # Let's verify and make sure they're executable
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
# Return the environment with our package
(pkgs.python3.withPackages (ps: [ httyCorePkg ])).overrideAttrs (old: {
  passthru = (old.passthru or { }) // {
    tests = { }; # Prevent blueprint from auto-generating problematic tests
  };
})
