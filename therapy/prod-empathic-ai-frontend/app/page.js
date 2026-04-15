import HomePageClient from "../components/HomePageClient.jsx";
import { resolveBackendApiBaseUrl } from "../lib/runtime";

export default function HomePage() {
  const apiBaseUrl = resolveBackendApiBaseUrl();

  return <HomePageClient apiBaseUrl={apiBaseUrl} />;
}
