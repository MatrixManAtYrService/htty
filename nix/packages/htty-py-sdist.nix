# Pure Python source package - Python code only, no ht binary
# Built using hatchling for proper Python source distribution
{ inputs, pkgs, ... }:

let
  # Get project metadata from pyproject.toml
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../py-envs/sdist/pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Include files needed for hatchling build
  pythonBuildSource = pkgs.lib.cleanSourceWith {
    src = ../..;
    filter = path: type:
      let
        baseName = baseNameOf path;
        # Get relative path from project root
        projectRoot = toString ../..;
        relPath = pkgs.lib.removePrefix projectRoot (toString path);
      in
        # Include Python source files  
        (pkgs.lib.hasPrefix "/src/python" relPath) ||
        # Include directory structure
        (relPath == "/src/python" && type == "directory") ||
        (relPath == "/src" && type == "directory") ||
        # Include py-envs directory and its contents
        (pkgs.lib.hasPrefix "/py-envs" relPath) ||
        (relPath == "/py-envs" && type == "directory") ||
        # Include license and readme
        (baseName == "LICENSE") ||
        (baseName == "README.md");
  };

  # Create sdist using hatchling
  htty-sdist = pkgs.stdenv.mkDerivation {
    pname = "htty-py-sdist";
    inherit version;
    src = pythonBuildSource;

    nativeBuildInputs = with pkgs; [
      python3
      python3Packages.hatchling
      python3Packages.build
    ];

    buildPhase = ''
      echo "Building Python source distribution with hatchling..."
      
      # Use the Python-only pyproject.toml
      cp py-envs/sdist/pyproject.toml pyproject.toml
      
      # Build the source distribution
      python -m build --sdist --outdir dist/
    '';

    installPhase = ''
      mkdir -p $out
      
      # Copy the sdist to output
      cp dist/*.tar.gz $out/
      
      # Also extract it for direct use
      mkdir -p $out/extracted
      cd $out/extracted
      tar -xzf $out/*.tar.gz --strip-components=1
    '';

    meta = with pkgs.lib; {
      description = "htty Python source distribution (hatchling-built)";
      license = licenses.mit;
    };
  };

  # Load workspace for Python dependencies
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../py-envs/sdist;
  };

  # Create Python package set
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay { 
        sourcePreference = "wheel";
      })
      # Override htty to use the hatchling-built source
      (final: prev: {
        htty = pkgs.stdenv.mkDerivation {
          pname = "htty-py-source";
          inherit version;
          src = "${htty-sdist}/extracted";
          
          installPhase = ''
            mkdir -p $out/lib/python3.12/site-packages
            # Copy Python source from hatchling sdist (package is at root level)
            cp -r htty $out/lib/python3.12/site-packages/
          '';
          
          meta = with pkgs.lib; {
            description = "htty Python source (from hatchling sdist)";
            license = licenses.mit;
          };
        };
      })
    ]
  );

in
# Create Python environment with htty from hatchling source distribution
pythonSet.mkVirtualEnv "htty-py-sdist" workspace.deps.default 