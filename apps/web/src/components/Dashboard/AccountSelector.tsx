'use client';

import { useAccounts } from '@/components/Providers';
import { ChevronDown } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function AccountSelector() {
  const { accounts, selectedAccountId, setSelectedAccount, isLoading, refreshAccounts } = useAccounts();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    refreshAccounts();
  }, [refreshAccounts]);

  const selectedAccount = accounts.find(a => a.account_id === selectedAccountId);

  if (!selectedAccount) {
    return <div className="text-slate-400 text-sm">Loading accounts...</div>;
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || accounts.length === 0}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg border border-slate-700 bg-slate-900/50 hover:bg-slate-800 transition-colors disabled:opacity-50"
      >
        <div>
          <div className="text-sm font-medium text-slate-100">{selectedAccount.account_name}</div>
          <div className="text-xs text-slate-400">{selectedAccount.account_id}</div>
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && accounts.length > 0 && (
        <div className="absolute top-full mt-2 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-lg z-50">
          <div className="max-h-64 overflow-y-auto">
            {accounts.map(account => (
              <button
                key={account.account_id}
                onClick={() => {
                  setSelectedAccount(account.account_id);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-3 border-b border-slate-800 hover:bg-slate-800 transition-colors ${
                  account.account_id === selectedAccountId ? 'bg-slate-800' : ''
                }`}
              >
                <div className="text-sm font-medium text-slate-100">{account.account_name}</div>
                <div className="text-xs text-slate-400">{account.account_id}</div>
                <div className={`text-xs mt-1 ${account.status === 'Active' ? 'text-green-400' : 'text-red-400'}`}>
                  {account.status}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
