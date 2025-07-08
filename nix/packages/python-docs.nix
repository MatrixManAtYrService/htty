# Python documentation generation
{ flake, pkgs, inputs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage makeCheck;

  # Create a shell script that sets up the environment and runs pdoc
  pdocScript = pkgs.writeShellScript "pdoc-docs" ''
    set -euo pipefail

    # Set up Python environment
    export PYTHONPATH="htty-core/src/python:htty/src:$PYTHONPATH"

    # Ensure docs directory exists
    mkdir -p docs

    # Generate htty docs (main docs in root)
    cd htty
    pdoc --output-directory ../docs htty !htty.keys
    echo '📚 Generated htty docs in ./docs/ directory'
    cd ..

    # Generate htty-core docs (subdirectory)
    cd htty-core
    pdoc --output-directory ../docs/htty-core htty_core
    echo '📚 Generated htty-core docs in ./docs/htty-core/ directory'
    cd ..

    echo '📚 Documentation has been generated in docs/ directory'
  '';

  # Create a single check that generates all docs
  pdocCheck = makeCheck {
    name = "pdoc";
    description = "Generate API documentation for htty and htty-core";
    dependencies = with pkgs; [ ];
    command = ''
      nix develop .#pytest-htty --command bash ${pdocScript}
    '';
  };
in
createAnalysisPackage {
  name = "python-docs";
  description = "Python documentation generation";
  checks = {
    pdoc = pdocCheck;
  };
}
