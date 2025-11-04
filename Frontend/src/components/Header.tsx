import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { BookOpen, LogOut, Library } from "lucide-react";
import quizlyLogo from "@/assets/quizly-logo.png";
import authService from "@/lib/auth";

interface HeaderProps {
  isAuthenticated?: boolean;
  onLogout?: () => void;
}

const Header = ({ isAuthenticated = false, onLogout }: HeaderProps) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    authService.logout();
    sessionStorage.clear();
    onLogout?.();
    navigate("/auth");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 sm:h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2 sm:gap-3 hover:opacity-80 transition-opacity">
          <img src={quizlyLogo} alt="Quizly" className="h-8 w-8 sm:h-10 sm:w-10" />
          <span className="text-xl sm:text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
            Quizly
          </span>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-4">
          {isAuthenticated ? (
            <>
              <Button variant="ghost" asChild size="sm" className="hidden sm:flex">
                <Link to="/decks">
                  <Library className="mr-2 h-4 w-4" />
                  My Decks
                </Link>
              </Button>
              <Button variant="ghost" asChild size="sm" className="sm:hidden">
                <Link to="/decks">
                  <Library className="h-4 w-4" />
                </Link>
              </Button>
              <Button variant="ghost" asChild size="sm" className="hidden sm:flex">
                <Link to="/">
                  <BookOpen className="mr-2 h-4 w-4" />
                  Generate
                </Link>
              </Button>
              <Button variant="ghost" asChild size="sm" className="sm:hidden">
                <Link to="/">
                  <BookOpen className="h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" onClick={handleLogout} size="sm" className="hidden sm:flex">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
              <Button variant="outline" onClick={handleLogout} size="sm" className="sm:hidden">
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <Button variant="hero" asChild size="sm">
              <Link to="/auth">Sign In</Link>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;
