import type { Route } from "./+types/action-page";
import { Button, Box, Container, Typography } from "@mui/material";
import { useNavigate } from "react-router";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Agent Transfer App" },
    { name: "description", content: "Agent Transfer Application" },
  ];
}

export default function ActionPage() {
  const navigate = useNavigate();

  return (
    <main className="flex items-center justify-center min-h-screen">
      <Container maxWidth="sm">
        <Box className="flex flex-col items-center gap-8">
          <header className="flex flex-col items-center gap-4 w-full">
            <Typography variant="h3" className="text-center font-bold">
              Agent Transfer App
            </Typography>
            <Typography variant="body1" className="text-center text-gray-600 dark:text-gray-400">
              Manage agent transfers and requests
            </Typography>
          </header>

          <Box className="w-full space-y-4">
            <Button
              variant="contained"
              fullWidth
              size="large"
              onClick={() => navigate("/request")}
            >
              New Transfer Request
            </Button>

            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => navigate("/pending-transfers")}
            >
              View Pending Transfers
            </Button>

            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => navigate("/pending-transfers")}
            >
              upload excel or document - WIP
            </Button>
          </Box>
        </Box>
      </Container>
    </main>
  );
}
