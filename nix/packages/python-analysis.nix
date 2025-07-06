# Python code analysis tools
{ flake, pkgs, inputs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage ruffCheckCheck ruffFormatCheck makeFawltydepsCheck;

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
  makeFawltydepsForWorkspace = { workspaceRoot, name, description, ignoreUndeclared ? [ ], ignoreUnused ? [ ] }:
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

      # Create the check with custom description
      fawltydepsCheckBase = makeFawltydepsCheck {
        pythonEnv = pythonEnvWithScript;
        inherit ignoreUndeclared ignoreUnused;
      };
    in
    # Override the description to be more specific
    fawltydepsCheckBase // {
      inherit description;
    };

  pyrightHttyCore = lib.checks.makeCheck {
    name = "pyright-htty-core";
    description = "Python type checking for htty-core (htty-core/src/python)";
    dependencies = with pkgs; [ ]; # nix develop provides the environment
    command = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright htty-core/src/python"'';
    verboseCommand = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright htty-core/src/python --verbose"'';
  };

  pyrightHtty = lib.checks.makeCheck {
    name = "pyright-htty";
    description = "Python type checking for htty (htty/src/htty)";
    dependencies = with pkgs; [ ]; # nix develop provides the environment
    command = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright htty/src/htty"'';
    verboseCommand = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright htty/src/htty --verbose"'';
  };

  pyrightTests = lib.checks.makeCheck {
    name = "pyright-tests";
    description = "Python type checking for tests (tests/)";
    dependencies = with pkgs; [ ]; # nix develop provides the environment
    command = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright tests/"'';
    verboseCommand = ''nix develop .#pytest-htty --command bash -c "${testEnvWithFawltydeps}/bin/pyright tests/ --verbose"'';
  };

  # Create fawltydeps checks for each workspace
  fawltydepsHtty = makeFawltydepsForWorkspace {
    workspaceRoot = ../../htty;
    name = "htty";
    description = "Python dependency analysis for htty (htty/)";
    ignoreUndeclared = [ "htty_core" ]; # htty_core comes from local reference
    ignoreUnused = [ ];
  };

  fawltydepsHttyCore = makeFawltydepsForWorkspace {
    workspaceRoot = ../../htty-core;
    name = "htty-core";
    description = "Python dependency analysis for htty-core (htty-core/)";
    ignoreUndeclared = [ ];
    ignoreUnused = [ ];
  };

  fawltydepsTests = makeFawltydepsForWorkspace {
    workspaceRoot = ../../tests;
    name = "tests";
    description = "Python dependency analysis for tests (tests/)";
    ignoreUndeclared = [ "htty" "htty_core" ]; # These come from test environment
    ignoreUnused = [ "pyright" "pdoc" ]; # some tools are not imported
  };
in
createAnalysisPackage {
  name = "python-analysis";
  description = "Python code analysis";
  checks = {
    fawltydeps-htty = fawltydepsHtty;
    fawltydeps-htty-core = fawltydepsHttyCore;
    fawltydeps-tests = fawltydepsTests;
    pyright-htty-core = pyrightHttyCore;
    pyright-htty = pyrightHtty;
    pyright-tests = pyrightTests;
    ruff-check = ruffCheckCheck;
    ruff-format = ruffFormatCheck;
  };
}
