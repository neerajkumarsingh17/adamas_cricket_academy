import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { LedgerOnlinePayment, RecordPayment } from '../api/payment'
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

// --- Online collection --- //

export function useOnlinePaymentSetup() {
  return useQuery({
    queryKey: ['online-payments', 'setup'],
    queryFn: paymentApi.onlineSetup,
    staleTime: 5 * 60_000,
  })
}

export function useOnlinePayments() {
  return useQuery({
    queryKey: ['online-payments', 'list'],
    queryFn: paymentApi.onlineList,
    staleTime: 10_000,
  })
}

// Any online call can turn into a recorded payment (it was paid), so both
// the waiting list and the ledger list refresh afterwards.
function useOnlineMutation<TVars, TResult>(call: (vars: TVars) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: call,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['online-payments', 'list'] })
      void queryClient.invalidateQueries({ queryKey: ['payments'] })
    },
  })
}

export function useOnlineCheckout() {
  return useOnlineMutation((body: LedgerOnlinePayment) => paymentApi.onlineCheckout(body))
}

export function useOnlineSendLink() {
  return useOnlineMutation((body: LedgerOnlinePayment) => paymentApi.onlineSendLink(body))
}

export function useOnlineConfirm() {
  return useOnlineMutation(({ id, payload }: { id: string; payload: Record<string, string> }) =>
    paymentApi.onlineConfirm(id, payload),
  )
}

export function useOnlineSync() {
  return useOnlineMutation((id: string) => paymentApi.onlineSync(id))
}

export function useOnlineResend() {
  return useOnlineMutation((id: string) => paymentApi.onlineResend(id))
}

export function useOnlineCancel() {
  return useOnlineMutation((id: string) => paymentApi.onlineCancel(id))
}
