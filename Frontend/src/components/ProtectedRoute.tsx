import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import authService from "@/lib/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const navigate = useNavigate();

  useEffect(() => {
    // Check authentication on mount and whenever the component updates
    if (!authService.isAuthenticated()) {
      navigate("/auth", { replace: true });
    }
  }, [navigate]);

  // Only render children if authenticated
  if (!authService.isAuthenticated()) {
    return null;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
