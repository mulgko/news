import { Link } from "wouter";

export function Footer() {
  return (
    <footer className="bg-foreground text-background py-16 mt-20">
      <div className="container-wide grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="col-span-1 md:col-span-2">
          <Link href="/">
            <h2 className="text-3xl font-black font-display italic mb-6 cursor-pointer">
              The <span className="text-primary not-italic">Daily</span> Chronicle
            </h2>
          </Link>
          <p className="text-muted-foreground font-serif max-w-sm leading-relaxed">
            Delivering the most important stories from around the globe. Accurate, unbiased, and always first.
          </p>
        </div>
        
        <div>
          <h4 className="font-sans font-bold uppercase tracking-widest text-sm mb-6 text-primary">Sections</h4>
          <ul className="space-y-3 font-serif text-muted-foreground">
            <li><Link href="/?category=Technology" className="hover:text-white transition-colors">Technology</Link></li>
            <li><Link href="/?category=Business" className="hover:text-white transition-colors">Business</Link></li>
            <li><Link href="/?category=Science" className="hover:text-white transition-colors">Science</Link></li>
            <li><Link href="/?category=Health" className="hover:text-white transition-colors">Health</Link></li>
            <li><Link href="/?category=Entertainment" className="hover:text-white transition-colors">Entertainment</Link></li>
          </ul>
        </div>
        
        <div>
          <h4 className="font-sans font-bold uppercase tracking-widest text-sm mb-6 text-primary">About</h4>
          <ul className="space-y-3 font-serif text-muted-foreground">
            <li><a href="#" className="hover:text-white transition-colors">About Us</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
          </ul>
        </div>
      </div>
      
      <div className="container-wide border-t border-white/10 mt-12 pt-8 text-center text-sm text-muted-foreground font-sans">
        &copy; {new Date().getFullYear()} The Daily Chronicle. All rights reserved.
      </div>
    </footer>
  );
}
