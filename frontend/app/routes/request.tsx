import type { Route } from "./+types/request";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router";
import {
  TextField,
  Button,
  Box,
  Container,
  Typography,
  MenuItem,
  Alert,
  CircularProgress,
  Select,
  InputLabel,
  FormControl,
  OutlinedInput,
  Chip,
  Checkbox,
  Card,
  CardContent
} from "@mui/material";
import {
  submitAgentTransferForm,
  setFormData,
  resetForm,
} from "~/store/agentTransferSlice";
import { fetchCarriers } from "~/store/carrierSlice";
import type { RootState, AppDispatch } from "~/store/store";

const US_STATES = [
  "AL",
  "AK",
  "AZ",
  "AR",
  "CA",
  "CO",
  "CT",
  "DE",
  "FL",
  "GA",
  "HI",
  "ID",
  "IL",
  "IN",
  "IA",
  "KS",
  "KY",
  "LA",
  "ME",
  "MD",
  "MA",
  "MI",
  "MN",
  "MS",
  "MO",
  "MT",
  "NE",
  "NV",
  "NH",
  "NJ",
  "NM",
  "NY",
  "NC",
  "ND",
  "OH",
  "OK",
  "OR",
  "PA",
  "RI",
  "SC",
  "SD",
  "TN",
  "TX",
  "UT",
  "VT",
  "VA",
  "WA",
  "WV",
  "WI",
  "WY",
];





export function meta({}: Route.MetaArgs) {
  return [
    { title: "New Transfer Request" },
    { name: "description", content: "Submit a new agent transfer request" },
  ];
}

export default function Request() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { formData, loading, error, success } = useSelector(
    (state: RootState) => state.agentTransfer
  );
  const { carriers, loading: carrierLoading } = useSelector(
    (state: RootState) => state.carriers
  );

  useEffect(() => {
    dispatch(fetchCarriers());
  }, [dispatch]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    dispatch(
      setFormData({
        ...formData,
        [name]: value,
      })
    );
  };

  const handleCarrierChange = (e: any) => {
    const { value } = e.target;
    dispatch(
      setFormData({
        ...formData,
        carriers: typeof value === "string" ? value.split(",") : value,
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await dispatch(submitAgentTransferForm(formData));
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <Container maxWidth="lg" className="py-6">
        <Box className="mb-8">
          <Button
            variant="text"
            onClick={() => navigate("/")}
            className="mb-4"
          >
            ← Back
          </Button>
          <Typography variant="h4" className="font-bold">
            Agent Transfer Request
          </Typography>
        </Box>

        {/* Status Cards */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, 1fr)",
              md: "repeat(4, 1fr)",
            },
            gap: 2,
            mb: 8,
          }}
        >
        
         
        </Box>

        {/* Form Section */}
        <Card className="mb-8">
          <CardContent>
            <Typography variant="h6" className="font-bold mb-6">
              Create New Transfer Request
            </Typography>

            <Box
              component="form"
              onSubmit={handleSubmit}
              className="space-y-6"
            >
              {error && (
                <Alert severity="error" onClose={() => dispatch(resetForm())}>
                  {error}
                </Alert>
              )}

              {success && (
                <Alert
                  severity="success"
                  onClose={() => dispatch(resetForm())}
                >
                  Form submitted successfully! <Link to="/pending-transfers" className="underline">View status here</Link>
                </Alert>
              )}

              {/* Agent ID and Transfer Date Row */}
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
                <Box>
                  <TextField
                    fullWidth
                    label="Agent ID"
                    name="agent"
                    value={formData.agent}
                    onChange={handleChange}
                    required
                    variant="outlined"
                    placeholder="Search by name or NPN number..."
                    disabled={loading}
                  />
                </Box>
                <Box>
                  <TextField
                    fullWidth
                    label="Transfer Date"
                    type="date"
                    InputLabelProps={{
                      shrink: true,
                    }}
                    inputProps={{
                      placeholder: "mm/dd/yyyy",
                    }}
                    variant="outlined"
                    disabled={loading}
                  />
                </Box>
              </Box>

              {/* Carriers to Transfer */}
              <FormControl fullWidth disabled={loading || carrierLoading} required>
                <InputLabel>Carriers to Transfer</InputLabel>
                <Select
                  multiple
                  value={formData.carriers}
                  onChange={handleCarrierChange}
                  input={<OutlinedInput label="Carriers to Transfer" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {(selected as string[]).map((value) => (
                        <Chip key={value} label={value} />
                      ))}
                    </Box>
                  )}
                  MenuProps={{
                    PaperProps: {
                      style: {
                        maxHeight: 224,
                      },
                    },
                  }}
                >
                  {carriers.map((carrier) => (
                    <MenuItem key={carrier.id} value={carrier.name}>
                      <Checkbox
                        checked={formData.carriers.indexOf(carrier.name) > -1}
                      />
                      {carrier.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Reason for Transfer */}
              <TextField
                fullWidth
                label="Reason for Transfer"
                multiline
                rows={4}
                variant="outlined"
                placeholder="Explain reason for this transfer request"
                disabled={loading}
              />

              {/* Action Buttons */}
              <Box className="flex justify-end gap-3">
                <Button
                  variant="outlined"
                  onClick={() => navigate("/")}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading || carrierLoading}
                >
                  {loading ? (
                    <>
                      <CircularProgress size={20} className="mr-2" />
                      Submitting...
                    </>
                  ) : (
                    "Submit Request"
                  )}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Recent Transfer Requests Table
        <Card>
          <CardContent>
            <Typography variant="h6" className="font-bold mb-4">
              Recent Transfer Requests
            </Typography>

            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow className="bg-gray-200">
                    <TableCell className="font-semibold">Request ID</TableCell>
                    <TableCell className="font-semibold">Agent Name</TableCell>
                    <TableCell className="font-semibold">NPN Number</TableCell>
                    <TableCell className="font-semibold">Carriers</TableCell>
                    <TableCell className="font-semibold">Status</TableCell>
                    <TableCell className="font-semibold">Transfer Date</TableCell>
                    <TableCell className="font-semibold">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentRequests.map((request) => (
                    <TableRow key={request.id} hover>
                      <TableCell>{request.id}</TableCell>
                      <TableCell>{request.agentName}</TableCell>
                      <TableCell>{request.npnNumber}</TableCell>
                      <TableCell>{request.carriers}</TableCell>
                      <TableCell>{request.status}</TableCell>
                      <TableCell>{request.transferDate}</TableCell>
                      <TableCell>
                        <Button variant="text" size="small">
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card> */}
      </Container>
    </main>
  );
}
