import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { ArrowUpTrayIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { uploadK1Document } from '../api/k1';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const currentYear = new Date().getFullYear();
const taxYears = Array.from({ length: 10 }, (_, i) => currentYear - i);

export default function K1Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [taxYear, setTaxYear] = useState(currentYear - 1);
  const [entityId, setEntityId] = useState('');
  const [entities, setEntities] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    getEntities().then((res) => setEntities(toArray(res))).catch(() => {});
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type === 'application/pdf') {
      setFile(dropped);
      setError('');
    } else {
      setError('Please drop a PDF file.');
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file.');
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    setError('');
    try {
      const res = await uploadK1Document(file, taxYear, {
        entity: entityId || undefined,
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      // Navigate to review page
      navigate(`/k1/${res.data.id}/review`);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Upload failed.';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Upload K-1 Document</h1>
      </div>

      <Card>
        <div className="space-y-6 p-2">
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
              dragActive
                ? 'border-indigo-500 bg-indigo-50'
                : file
                ? 'border-green-400 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById('k1-file-input').click()}
          >
            <input
              id="k1-file-input"
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileSelect}
            />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <DocumentTextIcon className="h-12 w-12 text-green-500" />
                <p className="text-sm font-medium text-green-700">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button
                  type="button"
                  className="text-xs text-indigo-600 hover:underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                >
                  Remove &amp; choose another
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <ArrowUpTrayIcon className="h-12 w-12 text-gray-400" />
                <p className="text-sm text-gray-600">
                  <span className="font-medium text-indigo-600">Click to upload</span> or drag
                  and drop
                </p>
                <p className="text-xs text-gray-500">PDF files only, up to 10 MB</p>
              </div>
            )}
          </div>

          {/* Options */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tax Year *
              </label>
              <select
                value={taxYear}
                onChange={(e) => setTaxYear(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-md shadow-sm px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                {taxYears.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entity (optional)
              </label>
              <select
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                className="w-full border border-gray-300 rounded-md shadow-sm px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">— Select entity —</option>
                {entities.map((ent) => (
                  <option key={ent.id} value={ent.id}>
                    {ent.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Upload progress */}
          {uploading && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Uploading &amp; extracting...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-md bg-red-50 p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Upload button */}
          <div className="flex justify-end">
            <Button onClick={handleUpload} disabled={!file || uploading}>
              <ArrowUpTrayIcon className="h-4 w-4 mr-2" />
              {uploading ? 'Uploading...' : 'Upload & Extract'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
