import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { documentApi } from '../api/document'

export function useDocuments(status?: string) {
  return useQuery({
    queryKey: ['documents', status ?? 'all'],
    queryFn: () => documentApi.list({ status }),
    staleTime: 15_000,
  })
}

// One child's documents on the parent portal's detail page — scoped
// server-side to "own" already (apps.admissions.document.views.
// DocumentViewSet.filter_to_own), this just narrows the *list* to the one
// child being viewed rather than every child a multi-child parent has.
export function useOwnerDocuments(ownerObjectId: string | undefined) {
  return useQuery({
    queryKey: ['documents', 'owner', ownerObjectId],
    queryFn: () => documentApi.list({ ownerObjectId }),
    enabled: !!ownerObjectId,
    staleTime: 15_000,
  })
}

export function useDocumentTypes() {
  return useQuery({
    queryKey: ['master', 'document-types'],
    queryFn: documentApi.types,
    staleTime: 5 * 60_000,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      file,
      documentTypeId,
      ownerType,
      ownerId,
    }: {
      file: File
      documentTypeId: string
      ownerType: string
      ownerId: string
    }) => {
      const { upload_url, s3_key } = await documentApi.presign({
        document_type: documentTypeId,
        owner_type: ownerType,
        owner_id: ownerId,
        filename: file.name,
        mime: file.type,
      })
      await documentApi.uploadToS3(upload_url, file)
      return documentApi.confirm({
        document_type: documentTypeId,
        owner_type: ownerType,
        owner_id: ownerId,
        s3_key,
        filename: file.name,
        mime: file.type,
      })
    },
    onSuccess: (_document, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      // A document's status lives on the checklist item embedded in its
      // owning Admission (admission/state.py's documents_verified guard
      // reads that, not the Document list) — without this, the checklist
      // status shown on AdmissionDetailPage/MyAdmissionPage stays stale
      // ("pending") until a manual reload, even though the upload
      // succeeded.
      if (variables.ownerType === 'admission') {
        void queryClient.invalidateQueries({ queryKey: ['admissions'] })
      }
    },
  })
}

export function useVerifyDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => documentApi.verify(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })
}

export function useRejectDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => documentApi.reject(id, reason),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })
}
