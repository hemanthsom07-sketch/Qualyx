import { useParams } from "react-router-dom";

import PlaceholderPage from "./PlaceholderPage";

// Future implementation will call listExecutionRuns(testId) from
// ../api/client.
function TestHistoryPage() {
  const { testId } = useParams<{ testId: string }>();

  return (
    <PlaceholderPage
      title={`Execution history — test ${testId}`}
      description="Execution history UI (GET /tests/{id}/executions) is not implemented in this stage."
    />
  );
}

export default TestHistoryPage;
