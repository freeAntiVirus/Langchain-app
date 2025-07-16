const ScrollableTextBox = () => {
  const textItems = Array.from({ length: 100 }, (_, i) => `Random text item ${i + 1}`);

  return (
    <div className="h-[500px] overflow-y-auto p-4 border rounded-lg bg-white shadow w-full">
      {textItems.map((text, index) => (
        <p key={index} className="mb-2 text-sm text-gray-700">
          {text}
        </p>
      ))}
    </div>
  );
};

export default ScrollableTextBox;