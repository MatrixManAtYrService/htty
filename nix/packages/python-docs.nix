# Python documentation generation
{ flake, pkgs, inputs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage makeCheck;

  # Create a Python script for post-processing documentation
  postProcessScript = pkgs.writeText "post_process_docs.py" ''
    import re
    import subprocess
    import sys
    from pathlib import Path


    def get_command_output(command: str) -> str:
        """Run a command and return its output."""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                check=True,
                cwd="."  # Ensure we're in the right directory
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error running command: {e}"


    def process_html_file(file_path: Path) -> None:
        """Process an HTML file to replace template placeholders."""
        print(f"Processing {file_path}")

        with open(file_path, 'r') as f:
            content = f.read()

        # Replace # DOCS_OUTPUT: command placeholders
        def replace_output(match):
            command = match.group(1).strip()
            output = get_command_output(command)
            return output

        content = re.sub(r'# DOCS_OUTPUT:\s*([^\n]+)', replace_output, content)

        # Write back the processed content
        with open(file_path, 'w') as f:
            f.write(content)


    if __name__ == "__main__":
        docs_dir = Path("docs")

        # Process all HTML files in the docs directory
        for html_file in docs_dir.rglob("*.html"):
            process_html_file(html_file)

        print("✅ Post-processing complete")
  '';

  # Create a shell script that sets up the environment and runs pdoc
  pdocScript = pkgs.writeShellScript "pdoc-docs" ''
    set -euo pipefail

    # Set up Python environment
    export PYTHONPATH="htty-core/src/python:htty/src:$PYTHONPATH"

    # Ensure docs directory exists
    mkdir -p docs

    # Generate htty docs (main docs in root)
    cd htty
    pdoc --output-directory ../docs --template-directory ../docs/templates htty !htty.keys
    echo '📚 Generated htty docs in ./docs/ directory'
    cd ..

    # Generate htty-core docs (subdirectory)
    cd htty-core
    pdoc --output-directory ../docs/htty-core --template-directory ../docs/htty-core-templates htty_core
    echo '📚 Generated htty-core docs in ./docs/htty-core/ directory'
    cd ..

    # Post-process the generated docs to replace template placeholders
    echo '🔄 Post-processing documentation templates...'
    PYTHONPATH="htty-core/src/python:htty/src:$PYTHONPATH" python ${postProcessScript}

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
