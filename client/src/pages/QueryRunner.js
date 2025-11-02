import React, { useState, useEffect } from "react";
import api from "../api";
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  TextField,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Snackbar,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function QueryRunner() {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down("md"));
  const [query, setQuery] = useState("SELECT * FROM customers;");
  const [result, setResult] = useState(null);
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [feedback, setFeedback] = useState({
    open: false,
    type: "info",
    message: "",
  });
  const [expandedValue, setExpandedValue] = useState(null);

  const showFeedback = (type, message) =>
    setFeedback({ open: true, type, message });

  const fetchTables = async () => {
    try {
      const res = await api.get("/tables");
      setTables(res.data.tables);
    } catch {
      showFeedback("error", "Failed to fetch tables");
    }
  };

  const runQuery = async () => {
    setLoading(true);
    setErrorMsg("");
    setSelectedTable("");
    setResult(null);
    try {
      const res = await api.post("/execute", { query });
      setResult(res.data);
      showFeedback("success", "Query executed successfully");

      await fetchTables();
    } catch (err) {
      const msg = err.response?.data?.error || "Query failed";
      setErrorMsg(msg);
      showFeedback("error", msg);
    } finally {
      setLoading(false);
    }
  };

  const previewTable = async (table) => {
    if (!table) return;
    setSelectedTable(table);
    setLoading(true);
    setErrorMsg("");
    setResult(null);

    try {
      const res = await api.get(`/table/${table}`);
      const cols = (res.data.columns || []).map(
        (c) => c.column_name || c.name || c.column
      );
      const rows = res.data.sample || [];
      setResult({ columns: cols, rows });
      showFeedback("info", `Previewing ${table}`);
    } catch (err) {
      // ✅ use the backend message instead of static one
      const msg =
        err?.response?.data?.error ||
        err?.message ||
        `Failed to preview table: ${table}`;
      setErrorMsg(msg);
      showFeedback("error", msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  return (
    <Box sx={{ bgcolor: "#f7f9fc", minHeight: "100vh", p: { xs: 2, md: 3 } }}>
      <Typography variant="h4" fontWeight={600} mb={3}>
        SQL Runner Dashboard
      </Typography>

      <Grid container spacing={2}>
        {/* SQL Editor - Full Width */}
        <Grid item xs={12}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" mb={1}>
                SQL Editor
              </Typography>
              <TextField
                multiline
                fullWidth
                minRows={6}
                maxRows={10}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Write your SQL query here..."
              />
              <Box
                sx={{ display: "flex", justifyContent: "space-between", mt: 2 }}
              >
                <Button
                  variant="contained"
                  color="primary"
                  onClick={runQuery}
                  disabled={loading}
                >
                  {loading ? (
                    <CircularProgress size={22} color="inherit" />
                  ) : (
                    "Execute"
                  )}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Available Tables */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{ height: "100%", display: "flex", flexDirection: "column" }}
          >
            <CardContent sx={{ flexGrow: 1, overflowY: "auto" }}>
              <Typography variant="h6" mb={1}>
                Available Tables
              </Typography>
              <List dense>
                {tables.map((table) => (
                  <ListItemButton
                    key={table}
                    selected={table === selectedTable}
                    onClick={() => previewTable(table)}
                  >
                    <ListItemText primary={table} />
                  </ListItemButton>
                ))}
                {tables.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No tables found.
                  </Typography>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
        {/* Table Preview / Query Result / Error */}
        <Grid item xs={12} md={12}>
          <Card
            sx={{ height: "100%", display: "flex", flexDirection: "column" }}
          >
            <CardContent sx={{ flexGrow: 1, overflowX: "auto" }}>
              <Typography variant="h6" mb={1}>
                {selectedTable
                  ? `Table Preview: ${selectedTable}`
                  : result
                  ? "Query Result"
                  : errorMsg
                  ? "Error"
                  : "Result Viewer"}
              </Typography>

              {loading ? (
                <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
                  <CircularProgress />
                </Box>
              ) : errorMsg ? (
                <Paper
                  elevation={0}
                  sx={{
                    bgcolor: "#fee",
                    color: "#b71c1c",
                    p: 2,
                    borderRadius: 2,
                    border: "1px solid #f44336",
                  }}
                >
                  <Typography variant="body2" fontWeight={500}>
                    ⚠️ {errorMsg}
                  </Typography>
                </Paper>
              ) : result && result.rows && result.columns ? (
                <Table size="small" sx={{ minWidth: 400 }}>
                  <TableHead>
                    <TableRow>
                      {result.columns.map((col) => (
                        <TableCell key={col} sx={{ fontWeight: 600 }}>
                          {col}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.rows.map((row, i) => (
                      <TableRow key={i}>
                        {result.columns.map((col) => {
                          const val = row[col];
                          const isLong =
                            typeof val === "string" && val.length > 20;
                          return (
                            <TableCell
                              key={col}
                              sx={{
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                                maxWidth: 160,
                                cursor: isLong ? "pointer" : "default",
                              }}
                              onClick={() => isLong && setExpandedValue(val)}
                              title={isLong ? "Click to expand" : ""}
                            >
                              {isLong ? val.slice(0, 20) + "..." : val ?? "-"}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Run a query or select a table to preview its data.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Expand cell dialog */}
      <Dialog
        open={!!expandedValue}
        onClose={() => setExpandedValue(null)}
        fullWidth
      >
        <DialogTitle>Full Value</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ wordBreak: "break-word" }}>
            {expandedValue}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExpandedValue(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar feedback */}
      <Snackbar
        open={feedback.open}
        autoHideDuration={4000}
        onClose={() => setFeedback({ ...feedback, open: false })}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={() => setFeedback({ ...feedback, open: false })}
          severity={feedback.type}
          sx={{ width: "100%" }}
        >
          {feedback.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
