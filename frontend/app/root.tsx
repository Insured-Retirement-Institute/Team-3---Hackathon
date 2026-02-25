import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { Provider } from "react-redux";
import { ThemeProvider, createTheme } from "@mui/material/styles";

import type { Route } from "./+types/root";
import { store } from "./store/store";
import "./app.css";

// Raymond James–style: navy blue and gray
const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#003366" },
    secondary: { main: "#5c6b7a" },
    text: { primary: "#1a1a1a", secondary: "#4a4a4a" },
    background: { default: "#f5f5f5", paper: "#ffffff" },
  },
  components: {
    MuiInputLabel: {
      styleOverrides: {
        root: { color: "#4a4a4a" },
      },
    },
    MuiFormLabel: {
      styleOverrides: {
        root: { color: "#4a4a4a" },
      },
    },
    MuiTypography: {
      styleOverrides: {
        root: { color: "#1a1a1a" },
      },
    },
  },
});

export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <Provider store={store}>
        <Outlet />
      </Provider>
    </ThemeProvider>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="pt-16 p-4 container mx-auto">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
