import { useParams } from "react-router-dom";

import PlaceholderPage from "./PlaceholderPage";

// Future implementation will call getProject(projectId) and
// listTestDefinitions(projectId) from ../api/client.
function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <PlaceholderPage
      title={`Project ${projectId}`}
      description="Project detail + test list UI is not implemented in this stage."
    />
  );
}

export default ProjectDetailPage;
