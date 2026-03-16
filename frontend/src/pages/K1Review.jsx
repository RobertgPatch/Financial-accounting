import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { getK1Document, updateK1Document, confirmK1Document, populateK1Document } from '../api/k1';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { toArray } from '../api/utils';

const statusColors = { draft: 'yellow', confirmed: 'green' };

const Input = ({ label, value, onChange, type = 'text', disabled, className = '', ...rest }) => (
  <div className={className}>
    <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
    <input
      type={type}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="block w-full rounded-md border-gray-300 shadow-sm text-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:text-gray-500 py-1.5 px-2"
      {...rest}
    />
  </div>
);

const Checkbox = ({ label, checked, onChange, disabled }) => (
  <label className="flex items-center gap-2 text-sm">
    <input
      type="checkbox"
      checked={checked || false}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
    />
    <span className="text-gray-700">{label}</span>
  </label>
);

const Select = ({ label, value, onChange, options, disabled, className = '' }) => (
  <div className={className}>
    <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="block w-full rounded-md border-gray-300 shadow-sm text-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 py-1.5 px-2"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  </div>
);

const clone = (obj) => JSON.parse(JSON.stringify(obj));

const emptyPartnership = { ein: '', name: '', address: '', city: '', state: '', zip_code: '', irs_center: '', is_ptp: false };
const emptyPartner = {
  tin: '', name: '', address: '', city: '', state: '', zip_code: '',
  is_general_partner: false, is_domestic: true, entity_type: '', is_retirement_plan: false,
  profit_beginning_pct: null, profit_ending_pct: null,
  loss_beginning_pct: null, loss_ending_pct: null,
  capital_beginning_pct: null, capital_ending_pct: null,
  nonrecourse_beginning: null, nonrecourse_ending: null,
  qualified_nonrecourse_beginning: null, qualified_nonrecourse_ending: null,
  recourse_beginning: null, recourse_ending: null,
  has_lower_tier_liabilities: false, has_guarantee_obligations: false,
  section_704c_beginning: null, section_704c_ending: null, built_in_gain: null,
};
const emptyCapital = {
  beginning_balance: null, capital_contributed: null, net_income: null,
  other_increase_decrease: null, withdrawals: null, ending_balance: null, tax_basis_method: '',
};
const emptyItem = { line_number: '', code: '', description: '', amount: null, raw_text: '', is_supplemental: false };

export default function K1Review() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [doc, setDoc] = useState(null);
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [populating, setPopulating] = useState(false);
  const [populateResult, setPopulateResult] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dirty, setDirty] = useState(false);

  // Editable form state
  const [pInfo, setPInfo] = useState(clone(emptyPartnership));
  const [ptInfo, setPtInfo] = useState(clone(emptyPartner));
  const [items, setItems] = useState([]);
  const [capAcct, setCapAcct] = useState(clone(emptyCapital));
  const [docFields, setDocFields] = useState({ entity: '', asset: '', notes: '', tax_year: '', is_final: false, is_amended: false });

  const applyDoc = useCallback((d) => {
    setDoc(d);
    setPInfo({ ...clone(emptyPartnership), ...d.partnership_info });
    setPtInfo({ ...clone(emptyPartner), ...d.partner_info });
    setItems(d.income_items?.length ? d.income_items.map((it) => ({ ...it })) : []);
    setCapAcct({ ...clone(emptyCapital), ...d.capital_account });
    setDocFields({
      entity: d.entity || '',
      asset: d.asset || '',
      notes: d.notes || '',
      tax_year: d.tax_year || '',
      is_final: d.is_final || false,
      is_amended: d.is_amended || false,
    });
    setDirty(false);
  }, []);

  const load = () => {
    setLoading(true);
    Promise.all([getK1Document(id), getEntities(), getAssets()])
      .then(([d, e, a]) => {
        applyDoc(d.data);
        setEntities(toArray(e));
        setAssets(toArray(a));
      })
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load document.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const updatePInfo = (key, val) => { setPInfo((p) => ({ ...p, [key]: val })); setDirty(true); };
  const updatePtInfo = (key, val) => { setPtInfo((p) => ({ ...p, [key]: val })); setDirty(true); };
  const updateCapAcct = (key, val) => { setCapAcct((c) => ({ ...c, [key]: val })); setDirty(true); };
  const updateDocFields = (key, val) => { setDocFields((d) => ({ ...d, [key]: val })); setDirty(true); };
  const updateItem = (idx, key, val) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [key]: val } : it)));
    setDirty(true);
  };
  const addItem = () => { setItems((prev) => [...prev, { ...clone(emptyItem) }]); setDirty(true); };
  const removeItem = (idx) => { setItems((prev) => prev.filter((_, i) => i !== idx)); setDirty(true); };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        tax_year: docFields.tax_year || doc.tax_year,
        entity: docFields.entity || null,
        asset: docFields.asset || null,
        notes: docFields.notes || '',
        is_final: docFields.is_final,
        is_amended: docFields.is_amended,
        partnership_info: { ...pInfo },
        partner_info: { ...ptInfo },
        income_items: items.map(({ id: _id, ...rest }) => ({
          ...rest,
          amount: rest.amount != null && rest.amount !== '' ? rest.amount : null,
        })),
        capital_account: { ...capAcct },
      };
      const res = await updateK1Document(id, payload);
      applyDoc(res.data);
      setSuccess('Changes saved successfully.');
    } catch (err) {
      setError(err.response?.data?.error || 'Save failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async () => {
    if (dirty) {
      setError('Please save your changes before confirming.');
      return;
    }
    setConfirming(true);
    setError('');
    try {
      const res = await confirmK1Document(id);
      applyDoc(res.data);
      setSuccess('Document confirmed successfully.');
    } catch (err) {
      setError(err.response?.data?.error || 'Confirm failed.');
    } finally {
      setConfirming(false);
    }
  };

  const handlePopulate = async () => {
    setPopulating(true);
    setError('');
    try {
      const res = await populateK1Document(id);
      setPopulateResult(res.data);
      setSuccess(res.data.message || 'Portfolio populated successfully.');
    } catch (err) {
      setError(err.response?.data?.error || 'Populate failed.');
    } finally {
      setPopulating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (!doc) {
    return <div className="text-center py-20 text-gray-500">Document not found.</div>;
  }

  const isReadOnly = doc.status === 'confirmed';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Review K-1: {pInfo.name || doc.original_filename}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Tax Year {doc.tax_year} &middot; {doc.extraction_method === 'ocr' ? 'OCR extracted' : 'Text extracted'}
            {dirty && <span className="ml-2 text-amber-600 font-medium">&bull; Unsaved changes</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge color={statusColors[doc.status] || 'gray'}>{doc.status}</Badge>
          {!isReadOnly && (
            <>
              <Button onClick={handleSave} disabled={saving || !dirty}>
                {saving ? 'Saving...' : 'Save'}
              </Button>
              <Button onClick={handleConfirm} disabled={confirming || dirty}>
                {confirming ? 'Confirming...' : 'Confirm'}
              </Button>
            </>
          )}
          {isReadOnly && !populateResult && (
            <Button onClick={handlePopulate} disabled={populating}>
              {populating ? 'Populating...' : 'Populate Portfolio'}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
      {success && (
        <div className="rounded-md bg-green-50 p-3">
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {/* Two-panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: PDF viewer */}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Original PDF</h2>
          {doc.document ? (
            <iframe src={doc.document} className="w-full h-[600px] border rounded" title="K-1 PDF" />
          ) : (
            <p className="text-gray-400 text-sm">PDF not available.</p>
          )}
        </Card>

        {/* Right: Editable data */}
        <div className="space-y-4 overflow-y-auto max-h-[calc(100vh-12rem)]">

          {/* Document fields & Linking */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Document &amp; Linking</h2>
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Entity"
                value={docFields.entity}
                onChange={(v) => updateDocFields('entity', v || null)}
                disabled={isReadOnly}
                options={[{ value: '', label: '— None —' }, ...entities.map((e) => ({ value: e.id, label: e.name }))]}
              />
              <Select
                label="Asset"
                value={docFields.asset}
                onChange={(v) => updateDocFields('asset', v || null)}
                disabled={isReadOnly}
                options={[{ value: '', label: '— None —' }, ...assets.map((a) => ({ value: a.id, label: a.name }))]}
              />
              <Input label="Tax Year" type="number" value={docFields.tax_year} onChange={(v) => updateDocFields('tax_year', v)} disabled={isReadOnly} />
              <div className="flex items-end gap-4 pb-1">
                <Checkbox label="Final" checked={docFields.is_final} onChange={(v) => updateDocFields('is_final', v)} disabled={isReadOnly} />
                <Checkbox label="Amended" checked={docFields.is_amended} onChange={(v) => updateDocFields('is_amended', v)} disabled={isReadOnly} />
              </div>
            </div>
            <div className="mt-3">
              <Input label="Notes" value={docFields.notes} onChange={(v) => updateDocFields('notes', v)} disabled={isReadOnly} />
            </div>
          </Card>

          {/* Partnership Info */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Part I — Partnership Information</h2>
            <div className="grid grid-cols-2 gap-3">
              <Input label="EIN" value={pInfo.ein} onChange={(v) => updatePInfo('ein', v)} disabled={isReadOnly} placeholder="XX-XXXXXXX" />
              <Input label="Partnership Name" value={pInfo.name} onChange={(v) => updatePInfo('name', v)} disabled={isReadOnly} />
              <Input label="Address" value={pInfo.address} onChange={(v) => updatePInfo('address', v)} disabled={isReadOnly} className="col-span-2" />
              <Input label="City" value={pInfo.city} onChange={(v) => updatePInfo('city', v)} disabled={isReadOnly} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="State" value={pInfo.state} onChange={(v) => updatePInfo('state', v)} disabled={isReadOnly} />
                <Input label="ZIP" value={pInfo.zip_code} onChange={(v) => updatePInfo('zip_code', v)} disabled={isReadOnly} />
              </div>
              <Input label="IRS Center" value={pInfo.irs_center} onChange={(v) => updatePInfo('irs_center', v)} disabled={isReadOnly} />
              <div className="flex items-end pb-1">
                <Checkbox label="Publicly Traded Partnership" checked={pInfo.is_ptp} onChange={(v) => updatePInfo('is_ptp', v)} disabled={isReadOnly} />
              </div>
            </div>
          </Card>

          {/* Partner Info */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Part II — Partner Information</h2>
            <div className="grid grid-cols-2 gap-3">
              <Input label="TIN" value={ptInfo.tin} onChange={(v) => updatePtInfo('tin', v)} disabled={isReadOnly} placeholder="XXX-XX-XXXX" />
              <Input label="Partner Name" value={ptInfo.name} onChange={(v) => updatePtInfo('name', v)} disabled={isReadOnly} />
              <Input label="Address" value={ptInfo.address} onChange={(v) => updatePtInfo('address', v)} disabled={isReadOnly} className="col-span-2" />
              <Input label="City" value={ptInfo.city} onChange={(v) => updatePtInfo('city', v)} disabled={isReadOnly} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="State" value={ptInfo.state} onChange={(v) => updatePtInfo('state', v)} disabled={isReadOnly} />
                <Input label="ZIP" value={ptInfo.zip_code} onChange={(v) => updatePtInfo('zip_code', v)} disabled={isReadOnly} />
              </div>
              <Select
                label="Entity Type"
                value={ptInfo.entity_type}
                onChange={(v) => updatePtInfo('entity_type', v)}
                disabled={isReadOnly}
                options={[
                  { value: '', label: '— Select —' },
                  { value: 'Individual', label: 'Individual' },
                  { value: 'Corporation', label: 'Corporation' },
                  { value: 'S Corporation', label: 'S Corporation' },
                  { value: 'Trust', label: 'Trust' },
                  { value: 'Estate', label: 'Estate' },
                  { value: 'Partnership', label: 'Partnership' },
                  { value: 'LLC', label: 'LLC' },
                ]}
              />
              <div className="flex items-end gap-4 pb-1">
                <Checkbox label="General Partner" checked={ptInfo.is_general_partner} onChange={(v) => updatePtInfo('is_general_partner', v)} disabled={isReadOnly} />
                <Checkbox label="Domestic" checked={ptInfo.is_domestic} onChange={(v) => updatePtInfo('is_domestic', v)} disabled={isReadOnly} />
              </div>
            </div>

            <h3 className="text-sm font-medium text-gray-700 mt-4 mb-2">Section J — Percentages</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="text-xs text-gray-400" />
              <div className="text-xs text-gray-400 text-center">Beginning</div>
              <div className="text-xs text-gray-400 text-center">Ending</div>
              {[
                ['Profit %', 'profit_beginning_pct', 'profit_ending_pct'],
                ['Loss %', 'loss_beginning_pct', 'loss_ending_pct'],
                ['Capital %', 'capital_beginning_pct', 'capital_ending_pct'],
              ].map(([label, beg, end]) => (
                <React.Fragment key={label}>
                  <div className="text-gray-600 flex items-center">{label}</div>
                  <Input value={ptInfo[beg]} onChange={(v) => updatePtInfo(beg, v || null)} disabled={isReadOnly} type="number" step="0.000001" />
                  <Input value={ptInfo[end]} onChange={(v) => updatePtInfo(end, v || null)} disabled={isReadOnly} type="number" step="0.000001" />
                </React.Fragment>
              ))}
            </div>

            <h3 className="text-sm font-medium text-gray-700 mt-4 mb-2">Section K — Liabilities</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="text-xs text-gray-400" />
              <div className="text-xs text-gray-400 text-center">Beginning</div>
              <div className="text-xs text-gray-400 text-center">Ending</div>
              {[
                ['Nonrecourse', 'nonrecourse_beginning', 'nonrecourse_ending'],
                ['Qual. Nonrecourse', 'qualified_nonrecourse_beginning', 'qualified_nonrecourse_ending'],
                ['Recourse', 'recourse_beginning', 'recourse_ending'],
              ].map(([label, beg, end]) => (
                <React.Fragment key={label}>
                  <div className="text-gray-600 flex items-center">{label}</div>
                  <Input value={ptInfo[beg]} onChange={(v) => updatePtInfo(beg, v || null)} disabled={isReadOnly} type="number" step="0.01" />
                  <Input value={ptInfo[end]} onChange={(v) => updatePtInfo(end, v || null)} disabled={isReadOnly} type="number" step="0.01" />
                </React.Fragment>
              ))}
            </div>
          </Card>

          {/* Income Items */}
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Part III — Income / Deductions</h2>
              {!isReadOnly && (
                <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                  + Add Line
                </button>
              )}
            </div>
            {items.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-gray-400 text-sm mb-2">No income items extracted.</p>
                {!isReadOnly && (
                  <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                    + Add your first line item
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="grid grid-cols-[60px_50px_1fr_120px_32px] gap-2 text-xs text-gray-400 font-medium px-1">
                  <div>Line</div>
                  <div>Code</div>
                  <div>Description</div>
                  <div className="text-right">Amount</div>
                  <div />
                </div>
                {items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-[60px_50px_1fr_120px_32px] gap-2 items-center">
                    <input
                      type="text"
                      value={item.line_number || ''}
                      onChange={(e) => updateItem(idx, 'line_number', e.target.value)}
                      disabled={isReadOnly}
                      className="block w-full rounded border-gray-300 text-sm font-mono py-1 px-1.5 disabled:bg-gray-100"
                      placeholder="#"
                    />
                    <input
                      type="text"
                      value={item.code || ''}
                      onChange={(e) => updateItem(idx, 'code', e.target.value)}
                      disabled={isReadOnly}
                      className="block w-full rounded border-gray-300 text-sm font-mono py-1 px-1.5 disabled:bg-gray-100"
                    />
                    <input
                      type="text"
                      value={item.description || ''}
                      onChange={(e) => updateItem(idx, 'description', e.target.value)}
                      disabled={isReadOnly}
                      className="block w-full rounded border-gray-300 text-sm py-1 px-1.5 disabled:bg-gray-100"
                      placeholder="Description"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={item.amount ?? ''}
                      onChange={(e) => updateItem(idx, 'amount', e.target.value || null)}
                      disabled={isReadOnly}
                      className="block w-full rounded border-gray-300 text-sm font-mono py-1 px-1.5 text-right disabled:bg-gray-100"
                      placeholder="0.00"
                    />
                    {!isReadOnly && (
                      <button
                        onClick={() => removeItem(idx)}
                        className="text-red-400 hover:text-red-600 text-lg leading-none"
                        title="Remove"
                      >&times;</button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Capital Account */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Section L — Capital Account</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                ['Beginning Balance', 'beginning_balance'],
                ['Capital Contributed', 'capital_contributed'],
                ['Net Income', 'net_income'],
                ['Other +/-', 'other_increase_decrease'],
                ['Withdrawals', 'withdrawals'],
                ['Ending Balance', 'ending_balance'],
              ].map(([label, key]) => (
                <Input
                  key={key}
                  label={label}
                  type="number"
                  step="0.01"
                  value={capAcct[key]}
                  onChange={(v) => updateCapAcct(key, v || null)}
                  disabled={isReadOnly}
                />
              ))}
              <Select
                label="Method"
                value={capAcct.tax_basis_method}
                onChange={(v) => updateCapAcct('tax_basis_method', v)}
                disabled={isReadOnly}
                options={[
                  { value: '', label: '— Select —' },
                  { value: 'Tax basis', label: 'Tax basis' },
                  { value: 'GAAP', label: 'GAAP' },
                  { value: 'Section 704(b)', label: 'Section 704(b)' },
                  { value: 'Other', label: 'Other' },
                ]}
              />
            </div>
          </Card>

          {/* Parser warnings */}
          {doc.notes && (
            <Card>
              <h2 className="text-sm font-semibold text-amber-700 mb-1">Parser Notes</h2>
              <p className="text-xs text-amber-600 whitespace-pre-wrap">{doc.notes}</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
