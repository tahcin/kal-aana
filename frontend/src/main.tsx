import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";
import { MotionConfig } from "motion/react";
import ErrorPage from "./components/ErrorPage";
import { Shell } from "./components/Shell";
import Chat from "./pages/Chat";
import "./index.css";
import { fetchJSON } from "./lib/api";
import NotFound from "./pages/NotFound";


const MapPage = lazy(() => import("./pages/MapPage"));
const Office = lazy(() => import("./pages/Office"));
const Offices = lazy(() => import("./pages/Offices"));
const Method = lazy(() => import("./pages/Method"));
const wait = <div className="h-[80vh]" />;

// A reload starts at the top of the page. Back and forward still return to where you were, but neither the browser nor
// React Router (which keeps positions in sessionStorage) restores the old position on a fresh load.
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
try { sessionStorage.removeItem("react-router-scroll-positions"); } catch { /* storage blocked */ }

// Every page shows something from the overview, so start fetching it now rather than after the first render.
void fetchJSON("/api/overview").catch(() => { /* the page shows its own error state */ });

const router = createBrowserRouter([
  {
    path: "/", element: <Shell />, errorElement: <ErrorPage />, children: [
      { index: true, element: <Chat /> },
      { path: "map", element: <Suspense fallback={wait}><MapPage /></Suspense> },
      { path: "offices", element: <Suspense fallback={wait}><Offices /></Suspense> },
      { path: "office/:id", element: <Suspense fallback={wait}><Office /></Suspense> },
      { path: "method", element: <Suspense fallback={wait}><Method /></Suspense> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <RouterProvider router={router} />
    </MotionConfig>
  </StrictMode>,
);
