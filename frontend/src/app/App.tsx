import { Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell';
import { PublicLayout } from '../components/layout/PublicLayout';
import { ProtectedRoute } from '../components/routing/ProtectedRoute';
import { ForgotPasswordPage } from '../features/auth/ForgotPasswordPage';
import { LoginPage } from '../features/auth/LoginPage';
import { ProfilePage } from '../features/auth/ProfilePage';
import { ChangePasswordPage } from '../features/auth/ChangePasswordPage';
import { ResetPasswordPage } from '../features/auth/ResetPasswordPage';
import { FranchiseDetailPage } from '../features/franchises/FranchiseDetailPage';
import { FranchisesPage } from '../features/franchises/FranchisesPage';
import { HomePage } from '../features/home/HomePage';
import { AdminGalleryPage } from '../features/gallery/AdminGalleryPage';
import { MenuPage } from '../features/products/MenuPage';
import { OwnerMenuPage } from '../features/products/OwnerMenuPage';
import { ProductDetailPage } from '../features/products/ProductDetailPage';
import { AboutPage } from '../features/public/AboutPage';
import { ContactPage } from '../features/public/ContactPage';
import { PublicHomePage } from '../features/public/HomePage';
import { PublicGalleryPage } from '../features/public/PublicGalleryPage';
import { PublicMenuPage } from '../features/public/PublicMenuPage';
import { EmployeesPage } from '../features/users/EmployeesPage';
import { UsersPage } from '../features/users/UsersPage';
import { PosPage } from '../features/pos/PosPage';
import { ThermalReceiptPage } from '../features/pos/ThermalReceiptPage';
import { BillsPage } from '../features/bills/BillsPage';
import { BillDetailPage } from '../features/bills/BillDetailPage';
import { GstSettingsPage } from '../features/settings/GstSettingsPage';
import { InactivityGuard } from '../features/auth/InactivityGuard';
import { OffersPage } from '../features/settings/OwnerOffersPage';
import { PromotionsPage } from '../features/settings/PromotionsPage';
import { DailySalesPage } from '../features/reports/DailySalesPage';
import { ReportsPage } from '../features/reports/ReportsPage';
import { AuditsPage } from '../features/audits/AuditsPage';
import { CreateAuditPage } from '../features/audits/CreateAuditPage';
import { AuditDetailPage } from '../features/audits/AuditDetailPage';

export default function App() {
  return (
    <>
    <InactivityGuard />
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<PublicHomePage />} />
        <Route path="menu" element={<PublicMenuPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="gallery" element={<PublicGalleryPage />} />
        <Route path="contact" element={<ContactPage />} />
      </Route>

      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route
          element={
            <ProtectedRoute roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER', 'EMPLOYEE']} />
          }
        >
          <Route path="print/receipt/:orderId" element={<ThermalReceiptPage />} />
        </Route>

        <Route element={<AppShell />}>
          <Route element={<ProtectedRoute roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER']} />}>
            <Route path="dashboard" element={<HomePage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="audit" element={<AuditsPage />} />
            <Route path="audit/new" element={<CreateAuditPage />} />
            <Route path="audit/:auditId" element={<AuditDetailPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['SYSTEM_ADMIN']} />}>
            <Route path="franchises" element={<FranchisesPage />} />
            <Route path="franchises/:franchiseId" element={<FranchiseDetailPage />} />
            <Route path="products" element={<MenuPage />} />
            <Route path="products/:productId" element={<ProductDetailPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="settings/gst" element={<GstSettingsPage />} />
            <Route path="settings/offers" element={<Navigate to="/admin/promotions" replace />} />
            <Route path="admin/promotions" element={<PromotionsPage />} />
            <Route path="admin/gallery" element={<AdminGalleryPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['FRANCHISE_OWNER']} />}>
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="owner/menu" element={<OwnerMenuPage />} />
            <Route path="owner/offers" element={<OffersPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['EMPLOYEE']} />}>
            <Route path="pos" element={<PosPage />} />
            <Route path="daily-sales" element={<DailySalesPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER', 'EMPLOYEE']} />}>
            <Route path="bills" element={<BillsPage />} />
            <Route path="bills/:orderId" element={<BillDetailPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['FRANCHISE_OWNER', 'EMPLOYEE']} />}>
            <Route path="profile" element={<ProfilePage />} />
          </Route>

          <Route element={<ProtectedRoute roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER']} />}>
            <Route path="change-password" element={<ChangePasswordPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  );
}
