#!/bin/sh
# Install custom n8n nodes from /custom_code/n8n-nodes directory

set -e

CUSTOM_NODES_DIR="/custom_code/n8n-nodes"
N8N_CUSTOM_DIR="/home/node/.n8n/custom"

echo "Installing custom n8n nodes from ${CUSTOM_NODES_DIR}..."

# Create custom directory if it doesn't exist with correct ownership
mkdir -p "${N8N_CUSTOM_DIR}"
chown -R node:node "${N8N_CUSTOM_DIR}"

# Check if custom_code directory exists and has nodes
if [ -d "${CUSTOM_NODES_DIR}" ]; then
    # Loop through each directory in n8n-nodes
    for node_dir in "${CUSTOM_NODES_DIR}"/*; do
        if [ -d "${node_dir}" ]; then
            node_name=$(basename "${node_dir}")
            echo "Found custom node: ${node_name}"

            # Check if package.json exists
            if [ -f "${node_dir}/package.json" ]; then
                echo "Installing ${node_name}..."

                # Check if this is a pre-built node with dist directory
                if [ -d "${node_dir}/dist" ] && [ -f "${node_dir}/index.js" ]; then
                    echo "Found pre-built node ${node_name}, copying directly..."

                    # Copy the entire node directory to custom folder
                    target_dir="${N8N_CUSTOM_DIR}/${node_name}"
                    rm -rf "${target_dir}"
                    cp -r "${node_dir}" "${target_dir}"

                    # Install production dependencies if node_modules doesn't exist
                    if [ ! -d "${target_dir}/node_modules" ]; then
                        cd "${target_dir}"
                        npm install --omit=dev --unsafe-perm 2>&1 || {
                            echo "Warning: Could not install dependencies for ${node_name}"
                        }
                    fi
                else
                    echo "Installing ${node_name} via npm..."
                    # Install the node package from the local directory
                    cd "${N8N_CUSTOM_DIR}"
                    npm install "${node_dir}" --no-save --unsafe-perm 2>&1 || {
                        echo "Error: Failed to install ${node_name}"
                        exit 1
                    }
                fi

                echo "✓ ${node_name} installed successfully"
            else
                echo "Skipping ${node_name} - no package.json found"
            fi
        fi
    done
else
    echo "No custom nodes directory found at ${CUSTOM_NODES_DIR}"
fi

# Ensure all files are owned by node user
chown -R node:node "${N8N_CUSTOM_DIR}"

echo "Custom node installation complete!"
