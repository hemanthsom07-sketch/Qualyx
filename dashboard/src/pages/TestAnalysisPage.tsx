import { useParams } from "react-router-dom";

import PlaceholderPage from "./PlaceholderPage";

// Future implementation will call getTestAnalysis(testId) from
// ../api/client.
function TestAnalysisPage() {
  const { testId } = useParams<{ testId: string }>();

  return (
    <PlaceholderPage
      title={`Flaky analysis — test ${testId}`}
      description="Flaky/recurring analysis UI (GET /tests/{id}/analysis) is not implemented in this stage."
    />
  );
}

export default TestAnalysisPage;
