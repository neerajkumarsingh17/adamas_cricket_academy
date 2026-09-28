import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { RecordPayment } from '../api/payment'
import { paymentApi } from '../api/payment'

export function usePayments(status?: string) {
  return useQuery({
    queryKey: ['payments', status ?? 'all'],
    queryFn: () => paymentApi.list({ status }),
    staleTime: 15_000,
  })
}

export function usePaymentTypes() {
  return useQuery({
    queryKey: ['master', 'payment-types'],
    queryFn: paymentApi.types,
    staleTime: 5 * 60_000,
  })
}

export function useRecordPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ body, idempotencyKey }: { body: RecordPayment; idempotencyKey: string }) =>
      paymentApi.record(body, idempotencyKey),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['payments'] }),
  })
}

export function useSettlePayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => paymentApi.settle(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['payments'] }),
  })
}
