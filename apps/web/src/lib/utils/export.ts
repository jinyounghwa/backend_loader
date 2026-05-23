export type ExportFormat = 'json' | 'csv';

interface ExportOptions {
  accountId?: string;
  connectionId?: string;
  startTime?: string;
  endTime?: string;
  format: ExportFormat;
}

/**
 * Export audit logs in specified format.
 *
 * @param options Export options including filters and format
 */
export async function exportAuditLogs(options: ExportOptions): Promise<void> {
  try {
    const params = new URLSearchParams();

    if (options.accountId) {
      params.append('account_id', options.accountId);
    }
    if (options.connectionId) {
      params.append('connection_id', options.connectionId);
    }
    if (options.startTime) {
      params.append('start_time', options.startTime);
    }
    if (options.endTime) {
      params.append('end_time', options.endTime);
    }
    params.append('format', options.format);

    const url = `/api/guardian/audit-logs/export?${params.toString()}`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Export failed with status ${response.status}`);
    }

    const content = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition');
    const filename =
      contentDisposition
        ?.split('filename="')[1]
        ?.split('"')[0] ||
      `audit-logs.${options.format}`;

    // Trigger download
    const downloadUrl = URL.createObjectURL(content);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Export error:', error);
    throw error;
  }
}
