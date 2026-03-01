import React, { useState, useCallback } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import Button from '../ui/Button';
import { createLinkToken, exchangeToken } from '../../api/plaid';

/**
 * PlaidLink wrapper — triggers Plaid Link flow, exchanges token on success.
 */
export default function PlaidLink({ onSuccess, onError, buttonText = 'Link Account' }) {
  const [linkToken, setLinkToken] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchToken = async () => {
    setLoading(true);
    try {
      const { link_token } = await createLinkToken();
      setLinkToken(link_token);
    } catch (e) {
      onError?.(e.response?.data?.error || 'Failed to create link token');
      setLoading(false);
    }
  };

  const handleSuccess = useCallback(async (publicToken, metadata) => {
    try {
      const result = await exchangeToken({
        public_token: publicToken,
        institution: metadata.institution || {},
        accounts: metadata.accounts || [],
      });
      onSuccess?.(result);
    } catch (e) {
      onError?.(e.response?.data?.error || 'Failed to link account');
    }
  }, [onSuccess, onError]);

  const handleExit = useCallback(() => {
    setLinkToken(null);
    setLoading(false);
  }, []);

  const config = {
    token: linkToken,
    onSuccess: handleSuccess,
    onExit: handleExit,
  };

  const { open, ready } = usePlaidLink(config);

  // When link token is fetched, auto-open Plaid Link
  React.useEffect(() => {
    if (linkToken && ready) {
      open();
      setLoading(false);
    }
  }, [linkToken, ready, open]);

  return (
    <Button onClick={fetchToken} disabled={loading}>
      {loading ? 'Connecting...' : buttonText}
    </Button>
  );
}
