# Pure Python source package - uses uv2nix to read dependencies from root pyproject.toml
{ inputs, pkgs, ... }:

let
  # Include only Python source files for fast rebuilds
  pythonSourceOnly = pkgs.lib.cleanSourceWith {
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
      # Include pyproject.toml for reference
      (baseName == "pyproject.toml") ||
      # Include license and readme
      (baseName == "LICENSE") ||
      (baseName == "README.md");
  };

  # Load workspace from root pyproject.toml (which has htty + ansi2html dependencies)
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../..;
  };

  # Create Python package set with dependencies from root pyproject.toml
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
      # Override htty to use Python source only (no Rust compilation)
      (final: prev: {
        htty = prev.htty.overrideAttrs (old: {
          # Replace source with our Python-only source
          src = pythonSourceOnly;

          # Don't build anything, just copy Python source
          format = "other";

          # Simple copy operation
          installPhase = ''
            mkdir -p $out/${final.python.sitePackages}

            # Copy Python source directly
            cp -r src/python/htty $out/${final.python.sitePackages}/

            # Make sure directories are readable
            find $out -type d -exec chmod 755 {} \;
            find $out -type f -exec chmod 644 {} \;
          '';

          # Don't run any build steps
          dontConfigure = true;
          dontBuild = true;

          meta = old.meta // {
            description = "htty Python source (no Rust binary)";
          };
        });
      })
    ]
  );

in
# Create Python environment with htty (source) + dependencies (from root pyproject.toml)
pythonSet.mkVirtualEnv "htty-py-sdist" workspace.deps.default
