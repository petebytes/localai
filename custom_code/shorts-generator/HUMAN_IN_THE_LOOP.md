# Human-in-the-Loop Quote Approval

This document explains the human-in-the-loop (HITL) approval system implemented for the shorts generator workflow.

## Overview

The workflow now requires user approval before proceeding with image and video generation. This ensures that:
- Users can review AI-generated quotes before committing resources
- Users can edit quotes to better match their intent
- Users can reject unsuitable quotes without wasting GPU time

## Architecture

The implementation uses the **Wait Step** pattern recommended by n8n best practices for interactive workflows.

### Flow Diagram

```
1. User triggers generation (via Gradio UI)
   ↓
2. n8n generates quote (or uses custom quote)
   ↓
3. **Wait for Quote Approval** node pauses workflow
   ↓
4. Gradio UI detects "waiting_for_approval" status
   ↓
5. User reviews quote and chooses:
   - Approve: Continue with original quote
   - Edit: Continue with modified quote
   - Reject: Cancel workflow
   ↓
6. Approval triggers resume webhook
   ↓
7. Workflow continues with approved/edited quote
   ↓
8. Generate image and video as normal
```

## Implementation Details

### 1. Models (`models.py`)

Added new models for approval workflow:

- `ExecutionStatus.WAITING_FOR_APPROVAL`: New status enum value
- `ApprovalAction`: Enum for approve/edit/reject actions
- `QuoteApprovalRequest`: Request model for approval endpoint
- `QuoteApprovalResponse`: Response model for approval endpoint

### 2. API (`api.py`)

Added new endpoint:

```python
POST /api/approve-quote
{
  "execution_id": "string",
  "action": "approve" | "edit" | "reject",
  "edited_quote": "optional string (required if action=edit)"
}
```

This endpoint resumes the n8n Wait node via webhook.

### 3. n8n Client (`n8n_client.py`)

Added functionality:

- `approve_quote()`: Sends approval decision to n8n Wait webhook
- Enhanced `_parse_execution_response()`: Detects when workflow is waiting at the Wait node

### 4. n8n Workflow (`short-inspirational-videos.json`)

Added three new nodes:

1. **Wait for Quote Approval** (Wait node)
   - Type: `n8n-nodes-base.wait`
   - Pauses workflow execution
   - Creates unique webhook: `/webhook-waiting/{execution_id}`
   - Note: webhookId is an internal identifier, not a URL suffix

2. **Handle Approval Response** (Code node)
   - Processes webhook payload from approval
   - Handles approve/edit/reject logic
   - Outputs final quote and approval status

3. **Check Approval Status** (If node)
   - Routes based on `approved` field
   - TRUE path: Continue to image generation
   - FALSE path: Workflow ends (rejected)

Updated connections:
- Both quote generation paths now go through the approval nodes
- Approved quotes proceed to "Image & Video Prompt Generator"

### 5. Gradio UI (`gradio_ui.py`)

Added approval interface:

**New Functions:**
- `approve_quote()`: Async function to call approval API
- `continue_after_approval()`: Generator that resumes polling after approval
- `update_approval_visibility()`: Helper to show/hide approval UI

**New UI Components:**
- `approval_group`: Collapsible section with approval buttons
- `edited_quote_input`: Textbox for editing quotes
- `approve_btn`: Button to approve quote as-is
- `edit_approve_btn`: Button to approve with edits
- `reject_btn`: Button to cancel workflow

**State Management:**
- `execution_id_state`: Stores execution ID across events
- `waiting_for_approval_state`: Tracks approval status

## User Experience

### Normal Flow (Approve)

1. User clicks "Generate Quote, Image & Video"
2. Status shows "Generating..."
3. After ~5 seconds, quote appears
4. Status changes to "Waiting for approval"
5. Approval section appears with the quote
6. User reviews and clicks "✓ Approve"
7. Workflow continues to image/video generation

### Edit Flow

1. Same as above until approval section appears
2. User modifies text in "Edit Quote" field
3. User clicks "✎ Edit & Approve"
4. Workflow continues with the edited quote
5. Final video uses the edited quote for speech

### Reject Flow

1. Same as above until approval section appears
2. User clicks "✗ Reject"
3. Workflow stops immediately
4. No image or video is generated
5. Status shows "Workflow cancelled"

## Technical Notes

### Wait Node Webhook

The n8n Wait node creates a unique webhook URL:
```
POST {N8N_BASE_URL}/webhook-waiting/{execution_id}
```

The payload must include:
```json
{
  "action": "approve|edit|reject",
  "approved": true|false,
  "approved_quote": "optional edited quote"
}
```

### Polling Behavior

- Initial polling: Checks every 1 second
- On `waiting_for_approval`: Polling stops, UI shows approval controls
- After approval: Polling resumes
- Timeout: 5 minutes (300 attempts)

### Error Handling

- Failed approval webhook: Shows error message
- Timeout waiting for approval: User can refresh page and check status
- Network errors: Displayed in status box

## Best Practices

Based on n8n community recommendations:

1. **Wait Step Pattern**: Used for short-lived, interactive workflows
2. **Webhook Resume**: Reliable method to continue execution
3. **State in UI**: Execution ID tracked in Gradio state
4. **User Feedback**: Clear status messages throughout

## Future Enhancements

Possible improvements:

1. **Approval Timeout**: Auto-reject after X minutes of inactivity
2. **Multi-User**: Support for approval by different users
3. **Approval History**: Log all approval decisions
4. **A/B Testing**: Generate multiple quotes, user picks best
5. **Slack/Discord Integration**: Approve via chat platforms

## Testing

To test the approval workflow:

1. Start the services:
   ```bash
   docker-compose up -d
   ```

2. Access Gradio UI at `http://localhost:7860`

3. Test scenarios:
   - Generate with approval
   - Generate with edit
   - Generate with rejection
   - Test timeout behavior

4. Verify in n8n UI:
   - Check execution history
   - Verify Wait node shows waiting state
   - Confirm approved quotes match final output

## Troubleshooting

### Workflow stuck at "Waiting for approval"

- Check n8n webhook is accessible
- Verify execution ID is correct
- Check n8n logs for webhook errors

### Approval not resuming workflow

- Verify n8n Wait node configuration
- Check webhook URL format: `/webhook-waiting/{execution_id}`
- Ensure payload matches expected format

### UI not showing approval buttons

- Check browser console for errors
- Verify API returns `waiting_for_approval` status
- Check Gradio state updates

## References

- [n8n Wait Node Documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/)
- [n8n HITL Best Practices](https://community.n8n.io/t/ideas-for-implementing-human-review-in-workflow/81096)
- [Gradio Event Handling](https://www.gradio.app/docs/gradio/events)
