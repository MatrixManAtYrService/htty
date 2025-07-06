# Python code analysis tools
{ flake, pkgs, inputs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage ruffCheckCheck ruffFormatCheck pyrightCheck makeFawltydepsCheck;

  # Load the test workspace which has fawltydeps as a regular dependency
  testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../tests;
  };

  testPythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (testWorkspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
    ]
  );

  # Create test environment with fawltydeps installed
  testEnvWithFawltydeps = testPythonSet.mkVirtualEnv "test-env-with-fawltydeps" testWorkspace.deps.default;

  # Function to create fawltydeps check for a specific workspace
  # Uses the test environment which has fawltydeps pre-installed
  makeFawltydepsForWorkspace = { workspaceRoot, name, ignoreUndeclared ? [ ], ignoreUnused ? [ ] }:
    let
      # Create a wrapper script that uses fawltydeps from test environment to analyze the workspace
      fawltydepsScript = pkgs.writeShellScript "fawltydeps-${name}" ''
        cd "${workspaceRoot}"
        ${testEnvWithFawltydeps}/bin/fawltydeps --code . "$@"
      '';

      # Create environment that uses the script
      pythonEnvWithScript = pkgs.runCommand "fawltydeps-${name}-env" { } ''
        mkdir -p $out/bin
        ln -s ${fawltydepsScript} $out/bin/fawltydeps
      '';
    in
    makeFawltydepsCheck {
      pythonEnv = pythonEnvWithScript;
      inherit ignoreUndeclared ignoreUnused;
    };

  # Create fawltydeps checks for each workspace
  fawltydepsHtty = makeFawltydepsForWorkspace {
    workspaceRoot = ../../htty;
    name = "htty";
    ignoreUndeclared = [ "htty_core" ]; # htty_core comes from local reference
    ignoreUnused = [ ];
  };

  fawltydepsHttyCore = makeFawltydepsForWorkspace {
    workspaceRoot = ../../htty-core;
    name = "htty-core";
    ignoreUndeclared = [ ];
    ignoreUnused = [ ];
  };

  fawltydepsTests = makeFawltydepsForWorkspace {
    workspaceRoot = ../../tests;
    name = "tests";
    ignoreUndeclared = [ "htty" "htty_core" ]; # These come from test environment
    ignoreUnused = [ ];
  };
in
createAnalysisPackage {
  name = "python-analysis";
  description = "Python code analysis";
  checks = {
    ruff-check = ruffCheckCheck;
    ruff-format = ruffFormatCheck;
    pyright = pyrightCheck;
    fawltydeps-htty = fawltydepsHtty;
    fawltydeps-htty-core = fawltydepsHttyCore;
    fawltydeps-tests = fawltydepsTests;
  };
}