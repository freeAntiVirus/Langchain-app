import React from "react";
import { NavLink } from "react-router-dom";

const NavBar = () => (
  <nav className="bg-white border-gray-200 dark:bg-gray-900">
    <div className="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto p-4">
      <a
        href="https://flowbite.com/"
        className="flex items-center space-x-3 rtl:space-x-reverse"
      >
        <img
          src="https://flowbite.com/docs/images/logo.svg"
          className="h-8"
          alt="Flowbite Logo"
        />
        <span className="self-center text-2xl font-semibold whitespace-nowrap dark:text-white">
          HSCHub
        </span>
      </a>

      <div
        className="items-center justify-between hidden w-full md:flex md:w-auto"
        id="navbar-main"
      >
        <ul className="flex flex-col font-medium p-4 md:p-0 mt-4 border border-gray-100 rounded-lg bg-gray-50 md:space-x-8 rtl:space-x-reverse md:flex-row md:mt-0 md:border-0 md:bg-white dark:bg-gray-800 md:dark:bg-gray-900 dark:border-gray-700">
          <li>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? "block py-2 px-3 text-blue-700 dark:text-blue-500"
                  : "block py-2 px-3 text-gray-900 hover:bg-gray-100 md:hover:bg-transparent md:hover:text-blue-700 md:p-0 dark:text-white md:dark:hover:text-blue-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent"
              }
            >
              Home
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/ClassifyResources"
              className={({ isActive }) =>
                isActive
                  ? "block py-2 px-3 text-blue-700 dark:text-blue-500"
                  : "block py-2 px-3 text-gray-900 hover:bg-gray-100 md:hover:bg-transparent md:hover:text-blue-700 md:p-0 dark:text-white md:dark:hover:text-blue-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent"
              }
            >
              Classify Resources
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/practice"
              className={({ isActive }) =>
                isActive
                  ? "block py-2 px-3 text-blue-700 dark:text-blue-500"
                  : "block py-2 px-3 text-gray-900 hover:bg-gray-100 md:hover:bg-transparent md:hover:text-blue-700 md:p-0 dark:text-white md:dark:hover:text-blue-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent"
              }
            >
              Create Practice Set
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/generate"
              className={({ isActive }) =>
                isActive
                  ? "block py-2 px-3 text-blue-700 dark:text-blue-500"
                  : "block py-2 px-3 text-gray-900 hover:bg-gray-100 md:hover:bg-transparent md:hover:text-blue-700 md:p-0 dark:text-white md:dark:hover:text-blue-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent"
              }
            >
              Generate Questions
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/contact"
              className={({ isActive }) =>
                isActive
                  ? "block py-2 px-3 text-blue-700 dark:text-blue-500"
                  : "block py-2 px-3 text-gray-900 hover:bg-gray-100 md:hover:bg-transparent md:hover:text-blue-700 md:p-0 dark:text-white md:dark:hover:text-blue-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent"
              }
            >
              Contact
            </NavLink>
          </li>
        </ul>
      </div>
    </div>
  </nav>
);

export default NavBar;