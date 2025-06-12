import {
  CommandIcon,
  FilesIcon,
  GaugeIcon,
} from "@phosphor-icons/react/dist/ssr";
import {NavLink} from "react-router";

const Navbar = () => {
  const pages = [
    {name: "CONTROL PANEL", href: "/", icon: <CommandIcon size={20} />},
    {name: "DASHBOARD", href: "/dashboard", icon: <GaugeIcon size={20} />},
    {name: "RESULTS", href: "/results", icon: <FilesIcon size={20} />},
  ];

  return (
    <div className="flex w-full border-b justify-between shadow-sm p-4">
      <NavLink key={"home"} to="/">
        <div className="font-semibold flex flex-col">
          <div className="text-xl">CLUE</div>
          <div className="text-xs">DASHBOARD</div>
        </div>
      </NavLink>
      <div className="flex gap-8">
        {pages.map((page) => (
          <NavLink
            key={page.name}
            to={page.href}
            className={({isActive}) =>
              `flex items-center gap-1 text-sm font-medium ${
                isActive
                  ? "border-b-1 border-black"
                  : "border-b-1 border-transparent"
              }`
            }
            end
          >
            <div className="flex gap-1 h-2">
              {page.icon} {page.name}
            </div>
          </NavLink>
        ))}
      </div>
    </div>
  );
};

export default Navbar;
