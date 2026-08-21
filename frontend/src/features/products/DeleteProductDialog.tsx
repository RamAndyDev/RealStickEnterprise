import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { Button, ErrorBanner, Modal } from '../../components/ui';
import { deleteProduct } from '../../lib/productsApi';
import { apiErrorMessage } from '../franchises/status';
import {
  DELETE_PRODUCT_CONFIRM_MESSAGE,
  DELETE_PRODUCT_FALLBACK,
  DELETE_PRODUCT_TITLE,
  applyDeleteProductResult,
} from './deleteProduct';

type DeleteProductDialogProps = {
  productId: string;
  productName: string;
  onClose: () => void;
  onDeleted: () => void;
};

export function DeleteProductDialog({
  productId,
  productName,
  onClose,
  onDeleted,
}: DeleteProductDialogProps) {
  const [error, setError] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: () => deleteProduct(productId),
    onSuccess: () => {
      const result = applyDeleteProductResult(true);
      setError(result.error);
      onDeleted();
      onClose();
    },
    onError: (err) => {
      const result = applyDeleteProductResult(
        false,
        apiErrorMessage(err, DELETE_PRODUCT_FALLBACK),
      );
      setError(result.error);
    },
  });

  return (
    <Modal
      title={DELETE_PRODUCT_TITLE}
      onClose={onClose}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="muted" onClick={onClose} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          </Button>
        </div>
      }
    >
      <p className="text-sm text-[#1A1A18]">{DELETE_PRODUCT_CONFIRM_MESSAGE}</p>
      {productName ? (
        <p className="mt-1 text-sm font-medium text-[#5C5C56]">{productName}</p>
      ) : null}
      {error ? (
        <div className="mt-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}
    </Modal>
  );
}
