import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	IDataObject,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';

export class LlamaOrchestrator implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Llama Orchestrator',
		name: 'llamaOrchestrator',
		icon: 'file:llama.svg',
		group: ['transform'],
		version: 1,
		description: 'Interact with llama.cpp chat and manage GPU memory',
		defaults: {
			name: 'Llama Orchestrator',
		},
		credentials: [
			{
				name: 'llamaOrchestratorApi',
				required: false,
			},
		],
		inputs: ['main'],
		outputs: ['main'],
		properties: [
			{
				displayName: 'Service',
				name: 'service',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Llama.cpp Chat',
						value: 'llamaChat',
						description: 'OpenAI-compatible chat endpoint with multimodal support',
					},
					{
						name: 'Model Orchestrator',
						value: 'orchestrator',
						description: 'GPU memory management and model lifecycle',
					},
				],
				default: 'llamaChat',
			},
			// Llama Chat Operations
			{
				displayName: 'Chat Operation',
				name: 'chatOperation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						service: ['llamaChat'],
					},
				},
				options: [
					{
						name: 'Chat Completion',
						value: 'chatCompletion',
						description: 'Send a chat message and get a response',
						action: 'Send chat completion',
					},
					{
						name: 'Chat Completion with Tools',
						value: 'chatCompletionTools',
						description: 'Send a chat message with function calling support',
						action: 'Send chat completion with tools',
					},
					{
						name: 'Health Check',
						value: 'healthCheck',
						description: 'Check if llama.cpp service is healthy',
						action: 'Check service health',
					},
				],
				default: 'chatCompletion',
			},
			// Orchestrator Operations
			{
				displayName: 'Orchestrator Operation',
				name: 'orchestratorOperation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						service: ['orchestrator'],
					},
				},
				options: [
					{
						name: 'Get GPU Status',
						value: 'getStatus',
						description: 'Get current GPU memory usage and loaded models',
						action: 'Get GPU status',
					},
					{
						name: 'Load Model',
						value: 'loadModel',
						description: 'Load a model into GPU memory',
						action: 'Load model',
					},
					{
						name: 'Unload Model',
						value: 'unloadModel',
						description: 'Unload a model from GPU memory',
						action: 'Unload model',
					},
				],
				default: 'getStatus',
			},
			// Chat Completion Fields
			{
				displayName: 'Model',
				name: 'model',
				type: 'string',
				default: 'qwen3-vl-30b',
				required: true,
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'Model to use for completion',
			},
			{
				displayName: 'Message',
				name: 'message',
				type: 'string',
				typeOptions: {
					rows: 4,
				},
				default: '',
				required: true,
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'The message to send to the model',
			},
			{
				displayName: 'System Prompt',
				name: 'systemPrompt',
				type: 'string',
				typeOptions: {
					rows: 2,
				},
				default: 'You are a helpful AI assistant.',
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'System message to set context',
			},
			{
				displayName: 'Temperature',
				name: 'temperature',
				type: 'number',
				typeOptions: {
					minValue: 0,
					maxValue: 2,
					numberStepSize: 0.1,
				},
				default: 0.7,
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'Sampling temperature (0 = deterministic, higher = more random)',
			},
			{
				displayName: 'Max Tokens',
				name: 'maxTokens',
				type: 'number',
				default: 1000,
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'Maximum number of tokens to generate',
			},
			{
				displayName: 'Tools JSON',
				name: 'toolsJson',
				type: 'string',
				typeOptions: {
					rows: 10,
				},
				default: '[]',
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletionTools'],
					},
				},
				description: 'Array of tool definitions in JSON format (OpenAI function calling format)',
			},
			{
				displayName: 'Image URL',
				name: 'imageUrl',
				type: 'string',
				default: '',
				displayOptions: {
					show: {
						service: ['llamaChat'],
						chatOperation: ['chatCompletion', 'chatCompletionTools'],
					},
				},
				description: 'Optional: URL or base64 data URI of image for multimodal input',
			},
			// Model Orchestrator Fields
			{
				displayName: 'Model Name',
				name: 'modelName',
				type: 'options',
				options: [
					{
						name: 'Qwen3-VL-30B',
						value: 'qwen3-vl-30b',
					},
					{
						name: 'WhisperX',
						value: 'whisperx',
					},
					{
						name: 'Ovi-11B',
						value: 'ovi-11b',
					},
					{
						name: 'Wan2.1-14B',
						value: 'wan2.1-14b',
					},
				],
				default: 'qwen3-vl-30b',
				displayOptions: {
					show: {
						service: ['orchestrator'],
						orchestratorOperation: ['loadModel', 'unloadModel'],
					},
				},
				description: 'Model to load or unload',
			},
			{
				displayName: 'Service Name',
				name: 'serviceName',
				type: 'options',
				options: [
					{
						name: 'llama-cpp',
						value: 'llama-cpp',
					},
					{
						name: 'whisperx',
						value: 'whisperx',
					},
					{
						name: 'ovi',
						value: 'ovi',
					},
					{
						name: 'wan',
						value: 'wan',
					},
				],
				default: 'llama-cpp',
				displayOptions: {
					show: {
						service: ['orchestrator'],
						orchestratorOperation: ['loadModel'],
					},
				},
				description: 'Service that runs the model',
			},
			{
				displayName: 'Priority',
				name: 'priority',
				type: 'number',
				typeOptions: {
					minValue: 1,
					maxValue: 10,
				},
				default: 5,
				displayOptions: {
					show: {
						service: ['orchestrator'],
						orchestratorOperation: ['loadModel'],
					},
				},
				description: 'Priority (1=low, 10=high)',
			},
			{
				displayName: 'Force Unload',
				name: 'forceUnload',
				type: 'boolean',
				default: false,
				displayOptions: {
					show: {
						service: ['orchestrator'],
						orchestratorOperation: ['unloadModel'],
					},
				},
				description: 'Whether to force unload even if model is in use',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const credentials = await this.getCredentials('llamaOrchestratorApi');
		const llamaBaseUrl = (credentials?.llamaBaseUrl as string) || 'http://llama-cpp:8000';
		const orchestratorBaseUrl = (credentials?.orchestratorBaseUrl as string) || 'http://model-orchestrator:8000';

		for (let i = 0; i < items.length; i++) {
			try {
				const service = this.getNodeParameter('service', i) as string;

				if (service === 'llamaChat') {
					const operation = this.getNodeParameter('chatOperation', i) as string;

					if (operation === 'healthCheck') {
						const response = await this.helpers.httpRequest({
							method: 'GET',
							url: `${llamaBaseUrl}/health`,
							json: true,
						});
						returnData.push({ json: response });
					} else if (operation === 'chatCompletion' || operation === 'chatCompletionTools') {
						const model = this.getNodeParameter('model', i) as string;
						const message = this.getNodeParameter('message', i) as string;
						const systemPrompt = this.getNodeParameter('systemPrompt', i) as string;
						const temperature = this.getNodeParameter('temperature', i) as number;
						const maxTokens = this.getNodeParameter('maxTokens', i) as number;
						const imageUrl = this.getNodeParameter('imageUrl', i, '') as string;

						const messages: Array<IDataObject> = [];

						// Add system message
						if (systemPrompt) {
							messages.push({
								role: 'system',
								content: systemPrompt,
							});
						}

						// Add user message (with optional image)
						if (imageUrl) {
							messages.push({
								role: 'user',
								content: [
									{ type: 'text', text: message },
									{ type: 'image_url', image_url: { url: imageUrl } },
								],
							});
						} else {
							messages.push({
								role: 'user',
								content: message,
							});
						}

						const body: IDataObject = {
							model,
							messages,
							temperature,
							max_tokens: maxTokens,
						};

						// Add tools if provided
						if (operation === 'chatCompletionTools') {
							const toolsJson = this.getNodeParameter('toolsJson', i) as string;
							if (toolsJson) {
								try {
									body.tools = JSON.parse(toolsJson);
								} catch (error) {
									throw new NodeOperationError(this.getNode(), 'Invalid tools JSON');
								}
							}
						}

						const response = await this.helpers.httpRequest({
							method: 'POST',
							url: `${llamaBaseUrl}/v1/chat/completions`,
							body,
							json: true,
						});

						returnData.push({ json: response });
					}
				} else if (service === 'orchestrator') {
					const operation = this.getNodeParameter('orchestratorOperation', i) as string;

					if (operation === 'getStatus') {
						const response = await this.helpers.httpRequest({
							method: 'GET',
							url: `${orchestratorBaseUrl}/models/status`,
							json: true,
						});
						returnData.push({ json: response });
					} else if (operation === 'loadModel') {
						const modelName = this.getNodeParameter('modelName', i) as string;
						const serviceName = this.getNodeParameter('serviceName', i) as string;
						const priority = this.getNodeParameter('priority', i) as number;

						const response = await this.helpers.httpRequest({
							method: 'POST',
							url: `${orchestratorBaseUrl}/models/load`,
							body: {
								model: modelName,
								service: serviceName,
								priority,
							},
							json: true,
						});
						returnData.push({ json: response });
					} else if (operation === 'unloadModel') {
						const modelName = this.getNodeParameter('modelName', i) as string;
						const forceUnload = this.getNodeParameter('forceUnload', i) as boolean;

						const response = await this.helpers.httpRequest({
							method: 'POST',
							url: `${orchestratorBaseUrl}/models/unload`,
							body: {
								model: modelName,
								force: forceUnload,
							},
							json: true,
						});
						returnData.push({ json: response });
					}
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							error: error.message,
						},
						pairedItem: {
							item: i,
						},
					});
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
