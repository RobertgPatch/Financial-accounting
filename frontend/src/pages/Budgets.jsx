import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Button as MuiButton, IconButton, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, CircularProgress, Box, Alert, Tooltip,
} from '@mui/material';
import { Add, Delete, Edit, AccountBalance } from '@mui/icons-material';
import { getBudgets, createBudget, updateBudget, deleteBudget } from '../api/budgets';
import { getAssets } from '../api/assets';
import { getEntities } from '../api/entities';

const periodTypes = ['yearly', 'quarterly', 'monthly'];
const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);
const currentYear = new Date().getFullYear();
const years = Array.from({ length: 5 }, (_, i) => currentYear + 1 - i);
const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const emptyForm = {
  name: '', year: currentYear, period_type: 'yearly', quarter: '', month: '', notes: '', line_items: [],
};

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [assets, setAssets] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    const toArray = (res) => { const d = res.data?.results || res.data; return Array.isArray(d) ? d : []; };
    Promise.all([getBudgets(), getAssets(), getEntities()])
      .then(([b, a, e]) => {
        setBudgets(toArray(b));
        setAssets(toArray(a));
        setEntities(toArray(e));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => {
    setForm(emptyForm);
    setEditingId(null);
    setError('');
    setDialogOpen(true);
  };

  const openEdit = (budget) => {
    setForm({
      name: budget.name,
      year: budget.year,
      period_type: budget.period_type,
      quarter: budget.quarter || '',
      month: budget.month || '',
      notes: budget.notes || '',
      line_items: (budget.line_items || []).map(li => ({
        asset: li.asset,
        entity: li.entity || '',
        amount: li.amount,
        notes: li.notes || '',
      })),
    });
    setEditingId(budget.id);
    setError('');
    setDialogOpen(true);
  };

  const addLineItem = () => {
    setForm(f => ({ ...f, line_items: [...f.line_items, { asset: '', entity: '', amount: '', notes: '' }] }));
  };

  const removeLineItem = (index) => {
    setForm(f => ({ ...f, line_items: f.line_items.filter((_, i) => i !== index) }));
  };

  const updateLineItem = (index, field, value) => {
    setForm(f => ({
      ...f,
      line_items: f.line_items.map((li, i) => i === index ? { ...li, [field]: value } : li),
    }));
  };

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name,
        year: form.year,
        period_type: form.period_type,
        quarter: form.period_type === 'quarterly' ? form.quarter : null,
        month: form.period_type === 'monthly' ? form.month : null,
        notes: form.notes,
        line_items: form.line_items.map(li => ({
          asset: li.asset,
          entity: li.entity || null,
          amount: li.amount,
          notes: li.notes,
        })),
      };
      if (editingId) {
        await updateBudget(editingId, payload);
      } else {
        await createBudget(payload);
      }
      setDialogOpen(false);
      load();
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this budget?')) return;
    try { await deleteBudget(id); load(); } catch (e) { alert(e.response?.data ? JSON.stringify(e.response.data) : 'Failed to delete budget. Please try again.'); }
  };

  const getBudgetTotal = (budget) => {
    return (budget.line_items || []).reduce((sum, li) => sum + parseFloat(li.amount || 0), 0);
  };

  const periodLabel = (b) => {
    let label = `${b.year}`;
    if (b.period_type === 'quarterly' && b.quarter) label += ` Q${b.quarter}`;
    if (b.period_type === 'monthly' && b.month) label += ` ${months[b.month - 1]}`;
    return label;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccountBalance /> Budgets
            </Typography>
            <Typography variant="body2" color="text.secondary">{budgets.length} total</Typography>
          </Box>
          <MuiButton variant="contained" startIcon={<Add />} onClick={openAdd}>
            Add Budget
          </MuiButton>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
        ) : budgets.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h4" sx={{ mb: 1 }}>📋</Typography>
            <Typography color="text.secondary">No budgets yet. Create one to start planning.</Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ '& th': { fontWeight: 600, backgroundColor: '#f8fafc' } }}>
                  <TableCell>Name</TableCell>
                  <TableCell>Period</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Line Items</TableCell>
                  <TableCell>Total Budgeted</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {budgets.map(b => (
                  <TableRow key={b.id} hover>
                    <TableCell sx={{ fontWeight: 500 }}>{b.name}</TableCell>
                    <TableCell>{periodLabel(b)}</TableCell>
                    <TableCell>
                      <Chip label={b.period_type} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell>{(b.line_items || []).length}</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'success.main' }}>
                      {formatCurrency(getBudgetTotal(b))}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => openEdit(b)}>
                          <Edit fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => handleDelete(b.id)}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <form onSubmit={handleSave}>
          <DialogTitle>{editingId ? 'Edit Budget' : 'Create Budget'}</DialogTitle>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
            {error && <Alert severity="error">{error}</Alert>}

            <TextField label="Budget Name" required fullWidth value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField select label="Year" required value={form.year} sx={{ flex: 1 }}
                onChange={e => setForm(f => ({ ...f, year: parseInt(e.target.value) }))}>
                {years.map(y => <MenuItem key={y} value={y}>{y}</MenuItem>)}
              </TextField>
              <TextField select label="Period Type" required value={form.period_type} sx={{ flex: 1 }}
                onChange={e => setForm(f => ({ ...f, period_type: e.target.value }))}>
                {periodTypes.map(p => <MenuItem key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</MenuItem>)}
              </TextField>
              {form.period_type === 'quarterly' && (
                <TextField select label="Quarter" required value={form.quarter} sx={{ flex: 1 }}
                  onChange={e => setForm(f => ({ ...f, quarter: parseInt(e.target.value) }))}>
                  {[1,2,3,4].map(q => <MenuItem key={q} value={q}>Q{q}</MenuItem>)}
                </TextField>
              )}
              {form.period_type === 'monthly' && (
                <TextField select label="Month" required value={form.month} sx={{ flex: 1 }}
                  onChange={e => setForm(f => ({ ...f, month: parseInt(e.target.value) }))}>
                  {months.map((m, i) => <MenuItem key={i+1} value={i+1}>{m}</MenuItem>)}
                </TextField>
              )}
            </Box>

            <TextField label="Notes" multiline rows={2} fullWidth value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Line Items</Typography>
              <MuiButton size="small" startIcon={<Add />} onClick={addLineItem}>Add Line Item</MuiButton>
            </Box>

            {form.line_items.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                No line items yet. Add forecasted distributions for assets.
              </Typography>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& th': { fontWeight: 600, backgroundColor: '#f8fafc' } }}>
                      <TableCell>Asset</TableCell>
                      <TableCell>Entity (optional)</TableCell>
                      <TableCell>Forecasted Amount</TableCell>
                      <TableCell>Notes</TableCell>
                      <TableCell width={50}></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {form.line_items.map((li, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <TextField select fullWidth size="small" required value={li.asset}
                            onChange={e => updateLineItem(i, 'asset', e.target.value)}>
                            <MenuItem value="">Select asset...</MenuItem>
                            {assets.map(a => <MenuItem key={a.id} value={a.id}>{a.name}</MenuItem>)}
                          </TextField>
                        </TableCell>
                        <TableCell>
                          <TextField select fullWidth size="small" value={li.entity}
                            onChange={e => updateLineItem(i, 'entity', e.target.value)}>
                            <MenuItem value="">All entities</MenuItem>
                            {entities.map(e => <MenuItem key={e.id} value={e.id}>{e.name}</MenuItem>)}
                          </TextField>
                        </TableCell>
                        <TableCell>
                          <TextField type="number" fullWidth size="small" required
                            inputProps={{ min: 0, step: '0.01' }}
                            value={li.amount} onChange={e => updateLineItem(i, 'amount', e.target.value)} />
                        </TableCell>
                        <TableCell>
                          <TextField fullWidth size="small" value={li.notes}
                            onChange={e => updateLineItem(i, 'notes', e.target.value)} />
                        </TableCell>
                        <TableCell>
                          <IconButton size="small" color="error" onClick={() => removeLineItem(i)}>
                            <Delete fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <MuiButton onClick={() => setDialogOpen(false)}>Cancel</MuiButton>
            <MuiButton type="submit" variant="contained" disabled={saving}>
              {saving ? 'Saving...' : (editingId ? 'Update' : 'Create')}
            </MuiButton>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
}
