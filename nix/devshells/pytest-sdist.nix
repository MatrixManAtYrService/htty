# pytest devshell for pure Python unit tests (htty without htty-core dependency)
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;

  # Load the htty workspace directly
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../htty;
  };

  # Remove htty_core from dependencies for Python-only testing
  depsWithoutCore = builtins.removeAttrs workspace.deps.default [ "htty_core" ];

  # Override htty to remove htty_core dependency
  pyprojectOverrides = final: prev: {
    htty = prev.htty.overrideAttrs (old: {
      # Remove htty_core from dependencies
      propagatedBuildInputs = builtins.filter 
        (dep: !builtins.elem dep.pname or "" [ "htty_core" "htty-core" ])
        (old.propagatedBuildInputs or []);
    });
  };

  # Create python set without htty_core
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
        dependencies = depsWithoutCore;
      })
      pyprojectOverrides
    ]
  );

  # Create virtual environment with htty but no htty_core
  httyPythonOnly = pythonSet.mkVirtualEnv "htty-python-only" depsWithoutCore;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the Python-only htty environment (will fail without mocking htty_core)
  packages = [ httyPythonOnly ];

  # Add pyright for type checking
  extraBuildInputs = [ pkgs.pyright ];
}
