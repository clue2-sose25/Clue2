import {NavLink} from "react-router";

const Navbar = () => {
  const pages = [
    {name: "Control Panel", href: "/"},
    {name: "Results Analysis", href: "/results"},
    {name: "Previous Benchmarks", href: "/benchmarks"},
  ];

  return (
    <div className="flex w-full border-b justify-center">
      <div className="w-1/2 flex justify-between p-4">
        {pages.map((page) => {
          return <NavLink to={page.href}>{page.name}</NavLink>;
        })}
      </div>
    </div>
  );
};

export default Navbar;
