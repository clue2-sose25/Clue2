import {NavLink} from "react-router";

const Navbar = () => {
  const pages = [
    {name: "CONTROL PANEL", href: "/"},
    {name: "ANALYSIS", href: "/results"},
    {name: "ARCHIVE", href: "/benchmarks"},
    { name: "LOGS", href: "/logs" } 
  ];

  return (
    <div className="flex w-full border-b justify-between shadow-sm p-4 ">
      <div className="font-semibold flex flex-col">
        <div className="text-xl">CLUE</div>
        <div className="text-xs">DASHBOARD</div>
      </div>
      <div className="flex gap-8">
        {pages.map((page) => {
          return (
            <NavLink className="flex items-center text-sm" to={page.href}>
              {page.name}
            </NavLink>
          );
        })}
      </div>
    </div>
  );
};

export default Navbar;
