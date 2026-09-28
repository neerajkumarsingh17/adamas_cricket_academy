import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { LoginPage } from './auth/LoginPage'
import { RequireAuth } from './auth/RequireAuth'
import { AppShell } from './components/AppShell'
import { AdmissionDetailPage } from './features/admission/pages/AdmissionDetailPage'
import { AdmissionListPage } from './features/admission/pages/AdmissionListPage'
import { MyAdmissionPage } from './features/admission/pages/MyAdmissionPage'
import { DirectAdmission } from './features/admission/pages/DirectAdmission'
import { ApprovalsQueuePage } from './features/approvals/pages/ApprovalsQueuePage'
import { AttendanceReportPage } from './features/attendance/pages/AttendanceReportPage'
import { CorrectionsQueuePage } from './features/attendance/pages/CorrectionsQueuePage'
import { MarkAttendancePage } from './features/attendance/pages/MarkAttendancePage'
import { BatchListPage } from './features/batch/pages/BatchListPage'
import { BatchRosterPage } from './features/batch/pages/BatchRosterPage'
import { HomePage } from './features/dashboard/pages/HomePage'
import { DocumentVerificationQueuePage } from './features/document/pages/DocumentVerificationQueuePage'
import { EnquiryDetailPage } from './features/enquiry/pages/EnquiryDetailPage'
import { EnquiryFormPage } from './features/enquiry/pages/EnquiryFormPage'
import { EnquiryPipelinePage } from './features/enquiry/pages/EnquiryPipelinePage'
import { PublicEnquiryPage } from './features/enquiry/pages/PublicEnquiryPage'
import { IDCardListPage } from './features/idcard/pages/IDCardListPage'
import { LandingPage } from './features/landing/pages/LandingPage'
import { ParentChildDetailPage } from './features/parent/pages/ParentChildDetailPage'
import { ParentChildrenPage } from './features/parent/pages/ParentChildrenPage'
import { PaymentsPage } from './features/payment/pages/PaymentsPage'
import { StudentListPage } from './features/student/pages/StudentListPage'
import { MyPaymentsPage } from './features/student/pages/MyPaymentsPage'
import { ProfileCompletion } from './features/student/pages/ProfileCompletion'
import { StudentProfilePage } from './features/student/pages/StudentProfilePage'
import { TrialAssessmentPage } from './features/trial/pages/TrialAssessmentPage'
import { TrialCalendarPage } from './features/trial/pages/TrialCalendarPage'
import { TrialSlotDetailPage } from './features/trial/pages/TrialSlotDetailPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/enquire" element={<PublicEnquiryPage />} />

            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route path="/dashboard" element={<HomePage />} />

              <Route path="/enquiries" element={<EnquiryPipelinePage />} />
              <Route path="/enquiries/new" element={<EnquiryFormPage />} />
              <Route path="/enquiries/:id" element={<EnquiryDetailPage />} />

              <Route path="/trials" element={<TrialCalendarPage />} />
              <Route path="/trials/slots/:slotId" element={<TrialSlotDetailPage />} />
              <Route
                path="/trials/registrations/:registrationId/assess"
                element={<TrialAssessmentPage />}
              />

              <Route path="/admissions" element={<AdmissionListPage />} />
              <Route path="/admissions/new-direct" element={<DirectAdmission />} />
              <Route path="/admissions/:id" element={<AdmissionDetailPage />} />

              <Route path="/approvals" element={<ApprovalsQueuePage />} />
              <Route path="/my-admission" element={<MyAdmissionPage />} />
              <Route path="/my-payments" element={<MyPaymentsPage />} />

              <Route path="/students" element={<StudentListPage />} />
              <Route path="/students/:id" element={<StudentProfilePage />} />
              <Route path="/students/:id/profile-completion" element={<ProfileCompletion />} />

              <Route path="/documents" element={<DocumentVerificationQueuePage />} />
              <Route path="/payments" element={<PaymentsPage />} />
              <Route path="/id-cards" element={<IDCardListPage />} />

              <Route path="/batches" element={<BatchListPage />} />
              <Route path="/batches/:id" element={<BatchRosterPage />} />
              <Route path="/batches/:id/attendance-report" element={<AttendanceReportPage />} />
              <Route path="/sessions/:sessionId/mark" element={<MarkAttendancePage />} />
              <Route path="/attendance/corrections" element={<CorrectionsQueuePage />} />

              <Route path="/parent/children" element={<ParentChildrenPage />} />
              <Route path="/parent/children/:id" element={<ParentChildDetailPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
