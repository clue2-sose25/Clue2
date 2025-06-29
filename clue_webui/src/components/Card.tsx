import type { ReactElement } from "react";
import { Link } from "react-router";

const Card = ({
    title,
    icon,
    text,
    subText,
    link,
    button,
}: {
    title: string;
    icon: ReactElement;
    text: string;
    subText?: string;
    link: string;
    button: string;
}) => (
    <div className="w-72 h-72 bg-white rounded-xl shadow-md hover:shadow-lg transition flex flex-col justify-between p-6">
        <div className="flex flex-col items-center gap-6">
            <div className="text-xs font-medium">{title}</div>
            <div className="flex flex-col gap-2 justify-center align-center items-center h-full w-full">
                <div>{icon}</div>
                <div className="text-center font-semibold text-lg">{text}</div>
                {subText && <div className="text-xs text-gray-500 text-center">{subText}</div>}
            </div>
        </div>
        <Link
            to={link}
            className="mt-4 bg-blue-500 text-white rounded px-3 py-2 text-sm text-center hover:bg-blue-700"
        >
            {button}
        </Link>
    </div>
);

export default Card;
