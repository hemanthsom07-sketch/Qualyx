import { useParams } from "react-router-dom";

import PlaceholderPage from "./PlaceholderPage";

// Future implementation will call getTestDefinition(testId) and
// executeTestDefinition(testId) from ../api/client.
function TestDetailPage() {
  const { testId } = useParams<{ testId: string }>();

  return (
    <PlaceholderPage
      title={`Test ${testId}`}
      description="Test detail + execute UI is not implemented in this stage."
    />
  );
}

export default TestDetailPage;
