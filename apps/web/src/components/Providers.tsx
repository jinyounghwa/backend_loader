'use client';

import { AuthSessionProvider } from '@/components/layout/SessionProvider';
import { ToastProvider } from '@/components/ToastProvider';
import { ReactNode, createContext, useContext, useState, useCallback } from 'react';

export interface Account {
  account_id: string;
  account_name: string;
  account_email: string;
  arn: string;
  status: 'Active' | 'Suspended';
  joined_date: string;
}

interface AccountContextType {
  accounts: Account[];
  selectedAccountId: string | null;
  setSelectedAccount: (accountId: string) => void;
  isLoading: boolean;
  refreshAccounts: () => Promise<void>;
}

const AccountContext = createContext<AccountContextType | undefined>(undefined);

function AccountProvider({ children }: { children: ReactNode }) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refreshAccounts = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/accounts');
      if (res.ok) {
        const data = await res.json();
        setAccounts(data.accounts || []);
        if (data.accounts?.length && !selectedAccountId) {
          setSelectedAccountId(data.accounts[0].account_id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAccountId]);

  const contextValue: AccountContextType = {
    accounts,
    selectedAccountId,
    setSelectedAccount: setSelectedAccountId,
    isLoading,
    refreshAccounts,
  };

  return <AccountContext.Provider value={contextValue}>{children}</AccountContext.Provider>;
}

export function useAccounts() {
  const context = useContext(AccountContext);
  if (!context) {
    throw new Error('useAccounts must be used within AccountProvider');
  }
  return context;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthSessionProvider>
      <ToastProvider>
        <AccountProvider>
          {children}
        </AccountProvider>
      </ToastProvider>
    </AuthSessionProvider>
  );
}
