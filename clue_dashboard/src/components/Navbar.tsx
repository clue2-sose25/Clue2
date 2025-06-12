import {NavLink} from "react-router";

const Navbar = () => {
  const pages = [
    {name: "CONTROL PANEL", href: "/"},
    {name: "RESULTS", href: "/results"},
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
            <NavLink
              className="flex items-center text-sm"
              to={page.href}
              key={page.name}
            >
              {page.name}
            </NavLink>
          );
        })}
      </div>
    </div>
  );
};

export default Navbar;
