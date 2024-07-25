import itertools
import pathlib
import arcpy
import pandas as pd
import os


class ExportTablesToJSON:
    def __init__(self):
        self.gdb_path = r'A:\carrier_GROUP_data\02_mapping\carrier_group_mapping.gdb'
        # rel_folder = 'data'
        here_folder = os.path.dirname(os.path.dirname(__file__))
        print(f"Here Folder: {here_folder}")
        self.output_dir = os.path.join(here_folder, rel_folder)
        print(f"Output Directory: {self.output_dir}")
        arcpy.env.workspace = self.gdb_path
        arcpy.env.overwriteOutput = True

        # List of tables to export
        self.tables = ['command_ships']

    @property
    def unwanted_fields(self):
        return ['OBJECTID', "OID_", "Shape", "OID", "Shape_Length", "Shape_Area"]

    @property
    def table_index_fields(self):
        return {"command_ships": "hull_no"}

    def _table_to_df(self, intable):
        # Load table into pandas DataFrame
        # Cleanup up and format the data
        df = pd.read_csv(intable)
        # Drop unwanted fields
        for field in self.unwanted_fields:
            if field in df.columns:
                df = df.drop(field, axis=1)

        # Set table index
        tablename = os.path.basename(intable).split(".")[0]
        if self.table_index_fields[tablename] in df.columns:
            df = df.set_index(self.table_index_fields[tablename])
        else:
            print(f"Index field {self.table_index_fields[tablename]} not found in table {tablename}.")

        self._df_printer(df)

        return df

    def _export_to_CSV(self, intable):
        # Export table to CSV
        csv_path = os.path.join(self.output_dir, f'{intable}.csv')
        arcpy.conversion.TableToTable(intable, self.output_dir, f'{intable}.csv')
        return csv_path

    @staticmethod
    def _df_printer(df):
        print(f"--  DataFrame Info --")
        print(f'-- HEAD --')
        print(df.head())

        # Create groupings of 4 fields
        group_count = 4
        print(f'-- Fields --')
        printed = []
        print(f" Index: {df.index.name}")
        while printed != df.columns.to_list():
            for i in range(0, len(df.columns.to_list()), group_count):
                g = list(itertools.islice(df.columns.to_list(), i, i + group_count, None))
                print(f"   {g}")
                # subs = [f for f in g if f not in printed]
                printed.extend(g)

    def export_tables(self):

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for table in self.tables:
            out_csv = self._export_to_CSV(table)
            df = self._table_to_df(out_csv)

            # Export DataFrame to JSON
            json_path = os.path.join(self.output_dir, f'{table}.json')
            df.to_json(json_path, orient='index', date_format="iso", indent=4)

            print(os.listdir(self.output_dir))
            table_files = [f for f in os.listdir(self.output_dir) if pathlib.Path(f).stem == table]
            print(f"Table Files: {table_files}")
            not_json = [f for f in os.listdir(self.output_dir) if os.path.isfile(f) and (pathlib.Path(f).stem == table
                                                                                         and f != f'{table}.json')]
            print(f"Files not JSON: {not_json}")
            for f in not_json:
                os.remove(f)


ExportTablesToJSON().export_tables()
print("Export completed successfully.")
