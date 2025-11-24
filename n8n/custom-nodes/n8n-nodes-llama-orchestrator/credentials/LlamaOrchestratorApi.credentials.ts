import {
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class LlamaOrchestratorApi implements ICredentialType {
	name = 'llamaOrchestratorApi';
	displayName = 'Llama Orchestrator API';
	documentationUrl = 'https://llama.lan/docs';
	properties: INodeProperties[] = [
		{
			displayName: 'Llama.cpp Base URL',
			name: 'llamaBaseUrl',
			type: 'string',
			default: 'http://llama-cpp:8000',
			description: 'Base URL for the llama.cpp service',
		},
		{
			displayName: 'Model Orchestrator Base URL',
			name: 'orchestratorBaseUrl',
			type: 'string',
			default: 'http://model-orchestrator:8000',
			description: 'Base URL for the model orchestrator service',
		},
	];
}
