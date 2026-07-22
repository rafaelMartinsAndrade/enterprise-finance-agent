from datetime import datetime, timezone

from app.models.agent_run import AgentRun
from app.models.approval_request import ApprovalRequest
from app.models.tool_execution import ToolExecution
from app.repositories.base import Repository


class AgentRunRepository(Repository):
    def create_run(
        self,
        *,
        organization_id: int,
        document_id: int,
        version_id: int,
        initiated_by_user_id: int,
        thread_id: str,
        idempotency_key: str | None,
    ) -> AgentRun:
        record = AgentRun(
            organization_id=organization_id,
            document_id=document_id,
            version_id=version_id,
            initiated_by_user_id=initiated_by_user_id,
            thread_id=thread_id,
            idempotency_key=idempotency_key,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_run(self, run_id: int) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def get_run_by_idempotency_key(self, *, organization_id: int, idempotency_key: str) -> AgentRun | None:
        return (
            self.session.query(AgentRun)
            .filter(
                AgentRun.organization_id == organization_id,
                AgentRun.idempotency_key == idempotency_key,
            )
            .order_by(AgentRun.id.desc())
            .first()
        )

    def list_runs(self, organization_id: int) -> list[AgentRun]:
        return (
            self.session.query(AgentRun)
            .filter(AgentRun.organization_id == organization_id)
            .order_by(AgentRun.created_at.desc())
            .all()
        )

    def update_run(
        self,
        run: AgentRun,
        *,
        status: str,
        current_node: str | None,
        step_count: int,
        confidence_score: float,
        final_action: str | None,
        state_json: dict,
        last_error_message: str | None,
    ) -> AgentRun:
        run.status = status
        run.current_node = current_node
        run.step_count = step_count
        run.confidence_score = confidence_score
        run.final_action = final_action
        run.state_json = state_json
        run.last_error_message = last_error_message
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def create_or_update_approval(
        self,
        *,
        organization_id: int,
        agent_run_id: int,
        requested_by_user_id: int,
        request_payload_json: dict,
        status: str = "pending",
    ) -> ApprovalRequest:
        approval = self.get_latest_approval(agent_run_id)
        if approval is None or approval.status != "pending":
            approval = ApprovalRequest(
                organization_id=organization_id,
                agent_run_id=agent_run_id,
                requested_by_user_id=requested_by_user_id,
                request_payload_json=request_payload_json,
                status=status,
            )
        else:
            approval.request_payload_json = request_payload_json
            approval.status = status
        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)
        return approval

    def resolve_approval(
        self,
        approval: ApprovalRequest,
        *,
        status: str,
        resolved_by_user_id: int,
        decision_notes: str | None,
        edited_fields_json: dict,
    ) -> ApprovalRequest:
        approval.status = status
        approval.resolved_by_user_id = resolved_by_user_id
        approval.decision_notes = decision_notes
        approval.edited_fields_json = edited_fields_json
        approval.resolved_at = datetime.now(timezone.utc)
        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)
        return approval

    def get_latest_approval(self, agent_run_id: int) -> ApprovalRequest | None:
        return (
            self.session.query(ApprovalRequest)
            .filter(ApprovalRequest.agent_run_id == agent_run_id)
            .order_by(ApprovalRequest.id.desc())
            .first()
        )

    def create_tool_execution(
        self,
        *,
        organization_id: int,
        agent_run_id: int,
        tool_name: str,
        tool_type: str,
        status: str,
        duration_ms: int,
        arguments_json: dict,
        result_json: dict,
        error_message: str | None = None,
    ) -> ToolExecution:
        record = ToolExecution(
            organization_id=organization_id,
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            tool_type=tool_type,
            status=status,
            duration_ms=duration_ms,
            arguments_json=arguments_json,
            result_json=result_json,
            error_message=error_message,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_tool_executions(self, agent_run_id: int) -> list[ToolExecution]:
        return (
            self.session.query(ToolExecution)
            .filter(ToolExecution.agent_run_id == agent_run_id)
            .order_by(ToolExecution.id.asc())
            .all()
        )
