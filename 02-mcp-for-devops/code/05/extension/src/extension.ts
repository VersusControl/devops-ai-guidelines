import * as vscode from 'vscode';

/**
 * The extension does not talk to the MCP server directly. Instead it routes
 * user intent through GitHub Copilot Chat, which already has the
 * `k8s-mcp-server` registered via `.vscode/mcp.json`. This keeps a single
 * code path (the MCP protocol) responsible for all cluster operations.
 */

function getNamespace(): string {
    return vscode.workspace
        .getConfiguration('k8sMcp')
        .get<string>('defaultNamespace', 'default');
}

async function askNamespace(prompt: string): Promise<string | undefined> {
    return vscode.window.showInputBox({
        prompt,
        value: getNamespace(),
        validateInput: (v) => (v.trim().length === 0 ? 'namespace required' : null),
    });
}

async function dispatchChat(query: string): Promise<void> {
    await vscode.commands.executeCommand('workbench.action.chat.open', {
        query,
        mode: 'agent',
    });
}

export function activate(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('k8sMcp.listPods', async () => {
            const ns = await askNamespace('Namespace to list pods in');
            if (!ns) return;
            await dispatchChat(
                `Use the k8s-mcp-server tool \`list_pods\` for namespace \`${ns}\` and render the result as a compact table sorted by restarts.`,
            );
        }),

        vscode.commands.registerCommand('k8sMcp.scaleDeployment', async () => {
            const ns = await askNamespace('Namespace of the deployment');
            if (!ns) return;
            const name = await vscode.window.showInputBox({ prompt: 'Deployment name' });
            if (!name) return;
            const replicas = await vscode.window.showInputBox({
                prompt: 'Target replicas',
                validateInput: (v) => (/^\d+$/.test(v) ? null : 'must be a non-negative integer'),
            });
            if (!replicas) return;
            await dispatchChat(
                `Scale deployment \`${name}\` in namespace \`${ns}\` to ${replicas} replicas using \`scale_deployment\`. Follow the destructive-action confirmation rule.`,
            );
        }),

        vscode.commands.registerCommand('k8sMcp.tailLogs', async () => {
            const ns = await askNamespace('Namespace of the pod');
            if (!ns) return;
            const name = await vscode.window.showInputBox({ prompt: 'Pod name' });
            if (!name) return;
            await dispatchChat(
                `Call \`get_pod_logs\` for pod \`${name}\` in namespace \`${ns}\` with tailLines=200 and surface any ERROR / WARN lines.`,
            );
        }),
    );
}

export function deactivate(): void {
    /* no-op */
}
